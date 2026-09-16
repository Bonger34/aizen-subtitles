# -*- coding: utf-8 -*-
"""vl_recheck_new.py — 阶段2：对确定性规则无法判定的候选（V1近重复/V2互含/V3孤立短句）
用 PaddleOCR-VL-1.6-0.9B 复核（ts±1 三帧取最长），VL 有效则替换文本。

  - 读 subtitle_clean/[EP].json（当前库）
  - 候选集 = scan_noise.classify() 的标记项（V1/V2/V3）
  - VL 空/幻觉 → 保留原文本（兜底，与 hybrid_recheck 一致）
  - 写回前相邻 ±3s 同文本去重（防"变体对都被 VL 改成同一句"产生重复）
  - 审计输出: review/vl_recheck_new.json

用法: D:\paddle_env_vv\Scripts\python.exe -u vl_recheck_new.py --ep P01 [--frames 3]
"""
import cv2
import json
import os
import re
import sys
import time

import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from params import SUBTITLE_AREA
import scan_noise

os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(BASE, "Videos")
CLEAN_DIR = os.path.join(BASE, "subtitle_clean")
AUDIT = os.path.join(BASE, "review", "vl_recheck_new.json")

# 命令行
FRAMES = 3
EPS = []
SRC_DIR = CLEAN_DIR   # 输入（可与 CLEAN_DIR 不同：并行时用快照）
OUT_DIR = None        # None = 写回 SRC_DIR；并行时显式指定独立输出目录
args = sys.argv[1:]
while args:
    a = args.pop(0)
    if a == "--frames" and args:
        FRAMES = int(args.pop(0))
    elif a == "--src" and args:
        SRC_DIR = args.pop(0)
    elif a == "--out" and args:
        OUT_DIR = args.pop(0)
    else:
        EPS.append(a)
if OUT_DIR is None:
    OUT_DIR = SRC_DIR
os.makedirs(OUT_DIR, exist_ok=True)
OFFSETS = (0,) if FRAMES == 1 else ((0, 1) if FRAMES == 2 else (-1, 0, 1))

CJK_RE = re.compile(r'[\u4e00-\u9fff]')
HALLUCINATION_MARKS = [
    "人工智能语言模型", "我还没学习如何回答", "这是一个", "作为一个人工智能",
    "对不起", "抱歉，我", "无法回答", "我可以帮您", "您有什么问题",
    "图示为", "无法准确识别", "相关内容", "北京冬奥", "整体存在",
    "年1月1日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日",
    "请问", "仅供参考",
]


def vl_text_ok(t):
    t = t.strip()
    if not t:
        return False
    cjk = len(CJK_RE.findall(t))
    if cjk == 0 or cjk / len(t) < 0.4:
        return False
    for mark in HALLUCINATION_MARKS:
        if mark in t:
            return False
    return True


_vl_pipeline = None


def get_vl_pipeline():
    global _vl_pipeline
    if _vl_pipeline is None:
        t0 = time.time()
        print("加载 PaddleOCR-VL-1.6-0.9B（native/GPU）...", flush=True)
        from paddlex import create_pipeline
        from paddlex.inference.pipelines import load_pipeline_config
        cfg = load_pipeline_config("PaddleOCR-VL-1.6")
        cfg["use_doc_preprocessor"] = False
        cfg["use_layout_detection"] = False
        cfg["use_queues"] = False
        cfg["batch_size"] = 1
        cfg["use_chart_recognition"] = False
        cfg["use_seal_recognition"] = False
        cfg.get("SubModules", {}).pop("LayoutDetection", None)
        _vl_pipeline = create_pipeline(config=cfg, device="gpu:0")
        print(f"VL 模型加载完成，耗时 {time.time()-t0:.0f}s", flush=True)
    return _vl_pipeline


def vl_ocr_frame(frame_bgr):
    """VL 识别单帧字幕区，返回通过质量过滤的文本或空串"""
    try:
        pipe = get_vl_pipeline()
        crop = frame_bgr[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
        results = list(pipe.predict(
            crop,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_layout_detection=False,
            prompt_label="ocr",
            use_chart_recognition=False,
            use_seal_recognition=False,
            max_new_tokens=128,
            min_pixels=28 * 28 * 130,
            max_pixels=28 * 28 * 512,
        ))
        if not results:
            return ""
        res = results[0]
        blocks = res.get("parsing_res_list", []) if isinstance(res, dict) else []
        texts = []
        for b in blocks:
            c = b.get("content", "") if isinstance(b, dict) else getattr(b, "content", "")
            if isinstance(c, str) and c.strip():
                texts.append(c.strip())
        joined = "".join(texts)
        return joined if vl_text_ok(joined) else ""
    except Exception as e:
        print(f"  [VL ERROR] {type(e).__name__}: {str(e)[:120]}", flush=True)
        return ""


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def main():
    audit = []
    for fname in sorted(os.listdir(SRC_DIR)):
        if not fname.endswith('.json'):
            continue
        ep = fname.split(']')[0].lstrip('[')
        if EPS and ep not in EPS:
            continue
        path = os.path.join(SRC_DIR, fname)
        data = json.load(open(path, encoding='utf-8'))
        data.sort(key=lambda r: parse_ts(r.get('timestamp', '')) or 0)
        drop, marks = scan_noise.classify(data)
        marked = set(i for i, _ in marks)
        video = None
        for vf in sorted(os.listdir(VIDEO_DIR)):
            if vf.startswith(f'[{ep}]') and vf.lower().endswith('.mp4'):
                video = os.path.join(VIDEO_DIR, vf)
                break
        cap = cv2.VideoCapture(video) if video else None
        t0 = time.time()
        n_replaced = n_kept = 0
        changed = False
        for i, r in enumerate(data):
            if i not in marked:
                continue
            sec = parse_ts(r.get('timestamp', ''))
            best_text = ''
            if cap is not None and sec is not None:
                for off in OFFSETS:
                    t = sec + off
                    if t < 0:
                        continue
                    cap.set(cv2.CAP_PROP_POS_MSEC, int(t * 1000))
                    ret, frame = cap.read()
                    if not ret:
                        continue
                    txt = vl_ocr_frame(frame)
                    if len(txt) > len(best_text):
                        best_text = txt
            if best_text:
                new_text = best_text.replace(" ", "")
                if new_text != r['text']:
                    audit.append({'ep': ep, 'ts': r['timestamp'], 'typ': dict(marks)[i],
                                  'before': r['text'], 'after': new_text})
                    print(f"  {r['timestamp']} [{dict(marks)[i]}] {r['text'][:24]!r} → {new_text!r}", flush=True)
                    r['text'] = new_text
                    r['vl_rechecked'] = True
                    changed = True
                    n_replaced += 1
                else:
                    n_kept += 1
            else:
                r['vl_checked_kept'] = True
                n_kept += 1
        if cap is not None:
            cap.release()
        # 相邻 ±3s 同文本去重（VL 把变体对统一后可能重复）
        final = []
        for r in data:
            dup = False
            for o in final[-4:]:
                if o and o.get('text') == r.get('text') and \
                   abs((parse_ts(o.get('timestamp', '')) or 0) - (parse_ts(r.get('timestamp', '')) or 0)) <= 3:
                    # 保留 time 更早的一条：删除当前位置更晚的 r
                    dup = True
                    break
            if not dup:
                final.append(r)
        if changed and (len(final) != len(data) or any(e.get('vl_rechecked') for e in final)):
            json.dump(final, open(os.path.join(OUT_DIR, fname), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
        else:
            json.dump(data, open(os.path.join(OUT_DIR, fname), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
        print(f'{ep}: 标记{len(marked)} 替换{n_replaced} 保留{n_kept} 去重后 {len(data)}->{len(final)} 条，耗时 {time.time()-t0:.0f}s', flush=True)
    json.dump(audit, open(AUDIT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'审计: {AUDIT}（{len(audit)} 条替换）')


if __name__ == '__main__':
    main()
