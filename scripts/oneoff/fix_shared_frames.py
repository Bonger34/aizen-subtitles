# -*- coding: utf-8 -*-
"""修复"共用配图"问题: 给出错条目补抽它自己那句话的画面的帧。

流程(每集一趟顺序读帧, 不用 cap.set 跳转):
  1. 目标条目按其时间戳 ts 生成候选秒 [ts-3 .. ts+3];
  2. 读到候选秒就裁剪字幕区(y880-1050, 2x 上采样)二值化 OCR, 与条目文本算包含度;
  3. 取包含度最高的候选帧; >=0.8 视为找到;
  4. 落盘为新帧(绝不覆盖正在被别的条目使用的文件), 并把该条指向新帧。

用法:
  python fix_shared_frames.py                # 阶段1(±3s), 预演
  python fix_shared_frames.py --apply
  python fix_shared_frames.py --stage2 --apply   # 对未解决的用更宽窗口(±10s)再找
"""
import json
import os
import re
import sys

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
_ORT124 = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124'
if os.path.isdir(_NV_DLL):
    os.add_dll_directory(_NV_DLL)
    os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
if os.path.isdir(_ORT124):
    sys.path.insert(0, _ORT124)

import cv2
import numpy as np
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
FR = os.path.join(B, 'docs', 'frames')
FMAP = os.path.join(B, 'docs', 'frames_map.js')
SRC = os.path.join(B, 'review', 'shared_frames_ocr.json')
STAGE2_IN = os.path.join(B, 'review', 'shared_fix_unresolved.json')
OUT = os.path.join(B, 'review', 'shared_fix_result.json')
BAND = (100, 880, 1820, 1050)
WIN1, WIN2 = 3, 10
TAU = 0.8


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def sec(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2))


def ts_of(s):
    return f'{s // 60}m{s % 60:02d}s'


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def build_targets():
    rows = json.load(open(SRC, encoding='utf-8'))
    tg = []
    for r in rows:
        ep = r['frame'][:3]
        e = r['entries']
        v = r['verdict']
        if '后一条配图错' in v:
            bad = 1
        elif '前一条配图错' in v:
            bad = 0
        elif '都对不上' in v:
            bad = -1          # 两条都要补
        else:
            continue
        idxs = [0, 1] if bad == -1 else [bad]
        for i in idxs:
            ts, tx = e[i]
            tg.append({'ep': ep, 'ts': ts, 'sec': sec(ts), 'text': tx, 'old': r['frame']})
    return tg


def run(stage):
    targets = json.load(open(STAGE2_IN, encoding='utf-8')) if stage == 2 else build_targets()
    win = WIN2 if stage == 2 else WIN1
    by_ep = {}
    for t in targets:
        by_ep.setdefault(t['ep'], []).append(t)
    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
    })
    print(f'阶段{stage}: 目标 {len(targets)} 条, 窗口 ±{win}s', flush=True)

    for ep, ts_list in sorted(by_ep.items()):
        cap = cv2.VideoCapture(find_video(ep))
        fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        dur = total / fps
        want = {}
        for t in ts_list:
            t['best'] = None
            for d in range(-win, win + 1):
                s = t['sec'] + d
                if 0 <= s <= dur:
                    want.setdefault(int(round(s * fps)), []).append((t, s))
        n, ti = 0, 0
        order = sorted(want)
        while ti < len(order):
            if not cap.grab():
                break
            n += 1
            if n - 1 >= order[ti]:
                ok, frame = cap.retrieve()
                if ok:
                    for t, s in want[order[ti]]:
                        h, w = frame.shape[:2]
                        sy = h / 1080.0
                        c = frame[int(BAND[1] * sy):int(BAND[3] * sy),
                                  int(BAND[0] * (w / 1920.0)):int(BAND[2] * (w / 1920.0))]
                        c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
                        arr = c.copy()
                        mk = np.all(arr > 245, axis=2)
                        arr[mk] = [255, 255, 255]
                        arr[~mk] = [0, 0, 0]
                        try:
                            rr = ocr(arr)
                            got = norm(''.join(rr.txts) if rr.txts else '')
                        except Exception:
                            got = ''
                        want_t = norm(t['text'])
                        sc = sum(1 for ch in want_t if ch in got) / len(want_t) if want_t else 0.0
                        if t['best'] is None or sc > t['best'][2]:
                            t['best'] = (cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA),
                                         s, round(sc, 2), got)
                ti += 1
        cap.release()
        done = sum(1 for t in ts_list if t['best'] and t['best'][2] >= TAU)
        print(f'  {ep}: {len(ts_list)} 条, 达标 {done}', flush=True)

    apply = '--apply' in sys.argv
    MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;', open(FMAP, encoding='utf-8').read(), re.S).group(1))
    files = set(os.listdir(FR))
    ok_list, bad_list = [], []
    for t in targets:
        if not t['best']:
            bad_list.append(t)
            continue
        img, s, sc, got = t['best']
        if sc < TAU:
            bad_list.append(t)
            continue
        key = f"{t['ep']}|{t['ts']}"
        # 找到该条目的完整 key(含集名)
        full = [k for k in MAP if k.endswith('|' + t['ts']) and k.startswith(f"[{t['ep']}]")]
        if not full:
            bad_list.append(t)
            continue
        name = f"{t['ep']}_{t['ts']}.jpg"
        if name in files:
            name = f"{t['ep']}_{t['ts']}_fix.jpg"
        if apply:
            cv2.imwrite(os.path.join(FR, name), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            files.add(name)
            for k in full:
                MAP[k] = name
        ok_list.append({'ep': t['ep'], 'ts': t['ts'], 'text': t['text'], 'old': t['old'],
                        'new': name, 'found_at': ts_of(s), 'score': sc, 'ocr': got,
                        'key': full[0]})

    if apply:
        open(FMAP, 'w', encoding='utf-8').write('window.FRAMES_MAP = ' + json.dumps(MAP, ensure_ascii=False) + ';')
    lines = [f'阶段{stage} 结果: 修好 {len(ok_list)} / 未解决 {len(bad_list)}' + ('(已落盘)' if apply else '(预演)')]
    for r in ok_list:
        delta = sec(r['found_at']) - sec(r['ts'])
        lines.append(f"  {r['ep']} {r['ts']:>7s} [{r['text'][:22]:24s}] 命中于 {r['found_at']}({delta:+d}s, 分{r['score']}) -> {r['new']}")
    for t in bad_list:
        lines.append(f"  !! {t['ep']} {t['ts']:>7s} [{t['text'][:22]}] 未找到"
                     + (f" 最佳 {ts_of(t['best'][1])} 分{t['best'][2]}" if t.get('best') else ''))
    txt = '\n'.join(lines)
    open(os.path.join(B, 'review', f'shared_fix_stage{stage}.txt'), 'w', encoding='utf-8').write(txt)
    json.dump(bad_list, open(STAGE2_IN if stage == 1 else os.path.join(B, 'review', 'shared_fix_unresolved2.json'),
                             'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(ok_list, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(txt[:5000])


if __name__ == '__main__':
    run(2 if '--stage2' in sys.argv else 1)
