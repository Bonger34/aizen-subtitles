# hybrid_recheck.py — Hybrid 复核器：v5 server 全量结果 → VL 复核可疑条目
# 策略：
#   1. 读 subtitle_paddle_v5/[EP].json（v5 server 结果）
#   2. 筛"可疑条目"：文本含 ASCII(≥2字母) 或 假名(≥1)（水印/歌词/乱码残留）
#   3. 可疑条目从视频 ts±1 抽 3 帧 → VL 识别 → 取最长且通过质量过滤的文本
#   4. VL 结果有效则替换；VL 空/幻觉则保留 v5 原文本（兜底）
# 输出：subtitle_hybrid/[EP].json（不覆盖任何现有数据）+ 控制台统计
# 用法: D:\paddle_env_vv\Scripts\python.exe -u hybrid_recheck.py [--frames 1|2|3] [EP...]
#       --frames N 每条可疑条目抽 N 帧（默认 3：ts±1 窗口；1：仅 ts 精确帧，速度快 3 倍）
import cv2, os, re, json, sys, time
import numpy as np
import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from params import SUBTITLE_AREA

# 显存自动增长（4GB 显存跑 0.9B VL 必需）
os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(BASE, "Videos")
SRC_DIR = os.path.join(BASE, "archive/datasets/subtitle_paddle_v5")   # v5 server 全量结果
DST_DIR = os.path.join(BASE, "subtitle_hybrid")       # hybrid 复核结果
PATTERN = re.compile(r'^\[P(0[1-9]|1[0-9]|2[0-5])\]')

# 命令行解析：--frames N（默认 3）
FRAMES = 3
EPS = []
args = sys.argv[1:]
while args:
    a = args.pop(0)
    if a == "--frames" and args:
        FRAMES = int(args.pop(0))
    else:
        EPS.append(a)
# 帧窗口策略：1帧=ts精确帧(0,)；2帧=ts,ts+1；3帧=ts±1 全窗口
if FRAMES == 1:
    OFFSETS = (0,)
elif FRAMES == 2:
    OFFSETS = (0, 1)
else:
    OFFSETS = (-1, 0, 1)

# 可疑判定：ASCII(≥2字母) 或 假名
ASCII_RE = re.compile(r'[A-Za-z]{2,}')
KANA_RE = re.compile(r'[\u3040-\u30ff]')

# VL 质量过滤（与 compare_vl_p07.py 一致）
CJK_RE = re.compile(r'[\u4e00-\u9fff]')
HALLUCINATION_MARKS = [
    "人工智能语言模型", "我还没学习如何回答", "这是一个", "作为一个人工智能",
    "对不起", "抱歉，我", "无法回答", "我可以帮您", "您有什么问题",
    "图示为", "无法准确识别", "相关内容", "北京冬奥", "整体存在",
    "年1月1日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日",
    "请问", "仅供参考",
]

def vl_text_ok(t):
    """VL 帧文本质量过滤：无中文装饰帧/幻觉文本 → False"""
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

# ---------- VL 模型（延迟初始化） ----------
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
    """VL 识别单帧字幕区（裁剪，不做 2x 放大防 OOM），返回通过过滤的文本或空串"""
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
            min_pixels=28*28*130,
            max_pixels=28*28*512,
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
    m = re.match(r"(\d+)m(\d+)s", ts)
    if not m:
        return None
    return int(m.group(1))*60 + int(m.group(2))

def is_suspicious(text):
    """含 ASCII(≥2字母) 或 假名 → 可疑（需 VL 复核）"""
    return bool(ASCII_RE.search(text)) or bool(KANA_RE.search(text))

def recheck_one(video_title, entries):
    """复核一集：对可疑条目 VL 二次识别（ts±1 三帧取最长），替换/兜底"""
    video_path = os.path.join(VIDEO_DIR, video_title + ".mp4")
    cap = cv2.VideoCapture(video_path) if os.path.exists(video_path) else None
    stats = {"total": len(entries), "suspicious": 0, "replaced": 0, "kept": 0, "vl_time": 0.0}
    out = []
    for e in entries:
        text = e.get("text", "")
        if not is_suspicious(text):
            out.append(e)
            continue
        stats["suspicious"] += 1
        sec = parse_ts(e.get("timestamp", ""))
        best_text = ""
        if cap is not None and sec is not None:
            for off in OFFSETS:
                t = sec + off
                if t < 0:
                    continue
                cap.set(cv2.CAP_PROP_POS_MSEC, int(t*1000))
                ret, frame = cap.read()
                if not ret:
                    continue
                t0 = time.time()
                vl_txt = vl_ocr_frame(frame)
                stats["vl_time"] += time.time() - t0
                if len(vl_txt) > len(best_text):
                    best_text = vl_txt
        if best_text:
            # VL 有效：替换（去 VL 自带空格，与现有数据格式一致）
            new_e = dict(e)
            new_e["text"] = best_text.replace(" ", "")
            new_e["vl_rechecked"] = True
            out.append(new_e)
            stats["replaced"] += 1
        else:
            # VL 空/幻觉：兜底保留 v5 原文
            out.append(e)
            stats["kept"] += 1
    if cap is not None:
        cap.release()
    return out, stats

def main():
    os.makedirs(DST_DIR, exist_ok=True)
    print(f"复核模式: 每可疑条目 {FRAMES} 帧 (OFFSETS={OFFSETS})", flush=True)
    total_stats = {"total": 0, "suspicious": 0, "replaced": 0, "kept": 0, "vl_time": 0.0}
    for fname in sorted(os.listdir(SRC_DIR)):
        if not (fname.endswith(".json") and PATTERN.match(fname)):
            continue
        if EPS and not any(ep in fname for ep in EPS):
            continue
        video_title = fname[:-5]
        with open(os.path.join(SRC_DIR, fname), encoding="utf-8") as f:
            entries = json.load(f)
        t0 = time.time()
        results, stats = recheck_one(video_title, entries)
        total_stats["total"] += stats["total"]
        total_stats["suspicious"] += stats["suspicious"]
        total_stats["replaced"] += stats["replaced"]
        total_stats["kept"] += stats["kept"]
        total_stats["vl_time"] += stats["vl_time"]
        with open(os.path.join(DST_DIR, fname), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n{video_title[:24]}: 总{stats['total']} 可疑{stats['suspicious']} "
              f"替换{stats['replaced']} 保留{stats['kept']} 复核耗时{time.time()-t0:.0f}s", flush=True)
        # 打印替换明细（前 15 条）
        shown = 0
        for e in results:
            if e.get("vl_rechecked") and shown < 15:
                orig = [x["text"] for x in entries if x["timestamp"] == e["timestamp"]]
                print(f"  {e['timestamp']}: {orig[0] if orig else '?'}  →  {e['text']}")
                shown += 1
    print(f"\n=== 汇总 ===")
    print(f"总条数: {total_stats['total']}，可疑: {total_stats['suspicious']}，"
          f"VL 替换: {total_stats['replaced']}，保留 v5: {total_stats['kept']}")
    print(f"VL 复核耗时: {total_stats['vl_time']:.0f}s ({total_stats['vl_time']/max(total_stats['suspicious'],1):.1f}s/条)")
    print(f"输出: {DST_DIR}")

if __name__ == "__main__":
    main()
