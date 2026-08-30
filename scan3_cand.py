# -*- coding: utf-8 -*-
"""scan3_cand.py — 阶段1（vv_rob 环境）：rapidocr 粗筛候选帧

对无帧图台词窗口做 0.16s 步长粗扫，保存「检测到中文字幕文本」的候选帧
（最多 CAND_MAX 帧/条）到 review/cand_frames/，供阶段2 VL 精判。

用法: python scan3_cand.py [--test]
"""
import json
import os
import re
import sys

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
VIDEO_DIR = os.path.join(BASE, 'Videos')
FMAP_JS = os.path.join(BASE, 'Web', 'frames_map.js')
CAND_DIR = os.path.join(BASE, 'review', 'cand_frames')
SUBTITLE_AREA = (100, 895, 1820, 985)
RANGE_BEFORE = 500
RANGE_AFTER = 3500
FPS = 25.0
CAND_MAX = 16


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def load_missing():
    m = re.search(r'=\s*(\{.*?\})\s*;', open(FMAP_JS, encoding='utf-8').read(), re.S)
    FMAP = json.loads(m.group(1))
    out = {}
    for fname in sorted(os.listdir(CLEAN_DIR)):
        if not fname.endswith('.json'):
            continue
        ep = fname.split(']')[0].lstrip('[')
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            continue
        data = json.load(open(os.path.join(CLEAN_DIR, fname), encoding='utf-8'))
        missing = [r for r in data if f'{fname[:-5]}|{r.get("timestamp", "")}' not in FMAP]
        if missing:
            out[ep] = (video[0], missing)
    return out


def main():
    import os
    os.makedirs(CAND_DIR, exist_ok=True)
    # 清旧候选
    for f in os.listdir(CAND_DIR):
        os.remove(os.path.join(CAND_DIR, f))
    fast = RapidOCR()
    print('rapidocr 就绪', flush=True)
    test = '--test' in sys.argv
    channels = load_missing()
    if test:
        ep = 'P03'
        channels = {ep: (channels[ep][0],
                         [r for r in channels[ep][1] if r.get('timestamp') == '7m12s'])}
    total = sum(len(v[1]) for v in channels.values())
    print(f'待扫 {total} 条', flush=True)

    index = []
    for ep, (video, missing) in channels.items():
        cap = cv2.VideoCapture(video)
        for r in missing:
            sec = parse_ts(r.get('timestamp', ''))
            if sec is None:
                continue
            start_ms = sec * 1000 - RANGE_BEFORE
            end_ms = sec * 1000 + RANGE_AFTER
            cap.set(cv2.CAP_PROP_POS_MSEC, int(start_ms))
            t_ms = start_ms
            n_frames = int((end_ms - start_ms) / 1000 * FPS)
            got = []
            for _ in range(n_frames):
                ret, frame = cap.read()
                if frame is None:
                    break
                if len(got) >= CAND_MAX:
                    break
                crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3],
                             SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
                res, _ = fast(crop)
                otext = ''.join(x[1] for x in res) if res else ''
                if len(otext) >= 2:
                    tag = f'{ep}_{r.get("timestamp", "").replace("m", "M").replace("s", "S")}_{len(got)}'
                    fp = os.path.join(CAND_DIR, tag + '.jpg')
                    cv2.imwrite(fp, frame)
                    got.append({'ms': t_ms, 'file': tag + '.jpg', 'fast_text': otext[:40]})
                t_ms += int(1000 / FPS)
            index.append({'ep': ep, 'ts': r.get('timestamp', ''), 'text': r.get('text', ''),
                          'cands': got})
        cap.release()
        print(f'{ep}: 完成（累计条目 {len(index)}）', flush=True)

    with open(os.path.join(BASE, 'review', 'cand_index.json'), 'w', encoding='utf-8') as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
    print(f'候选条目 {len(index)}，保存 review/cand_index.json')


if __name__ == '__main__':
    main()
