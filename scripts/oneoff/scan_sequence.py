# -*- coding: utf-8 -*-
"""scan_sequence.py — 密集扫描生成字幕序列（0.2s 步长，v5/v6 GPU）

对窗口内逐 0.2s 帧识别字幕带，合并连续相同文本 → 完整字幕时间线。
解决「前后句漏句」：单帧判定看不到相邻对白，序列能看到。
用法: python scan_sequence.py   （扫描 12 条前后句窗口 + 用户点名 P19 6m16s）
输出: review/context_dense.json
"""
import glob
import json
import os

import cv2

from rapidocr import RapidOCR

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO_DIR = os.path.join(BASE, 'Videos')
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
SUBTITLE_AREA = (100, 895, 1820, 985)
STEP_MS = 200
WINDOW = 6          # ±6s

# 待查窗口（前后句 12 条 + 用户点名）
TARGETS = [
    ('P19', 376),      # 6m16s 用户点名
    ('P16', 608),      # 10m08s
    ('P19', 376),      # 6m16s dup 无碍
    ('P20', 279),      # 4m39s
    ('P22', 296),      # 4m56s
    ('P22', 1042),     # 17m22s
    ('P01', 321),      # 5m21s
    ('P01', 1482),     # 24m22s
    ('P02', 299),      # 4m59s
    ('P02', 412),      # 6m52s
    ('P02', 1159),     # 19m19s
    ('P08', 991),      # 16m31s
]


def parse_ts(ts):
    return int(ts.rstrip('s').split('m')[0]) * 60 + int(ts.split('m')[1].rstrip('s'))


def main():
    import re
    ocr = RapidOCR(params={'EngineConfig.onnxruntime.use_cuda': True})
    print('v5/v6 GPU 就绪', flush=True)

    result = {}
    video_cache = {}
    for ep, s in sorted(set(TARGETS)):
        if ep not in video_cache:
            vids = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                    if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
            video_cache[ep] = vids[0] if vids else None
        video = video_cache[ep]
        if not video:
            continue
        cap = cv2.VideoCapture(video)
        t0 = (s - WINDOW) * 1000
        t1 = (s + WINDOW) * 1000
        seq = []          # (start_ms, text)
        cur = None
        t = t0
        while t <= t1:
            cap.set(cv2.CAP_PROP_POS_MSEC, int(t))
            ret, frame = cap.read()
            if frame is None:
                t += STEP_MS
                continue
            crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3],
                         SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
            res = ocr(crop)
            txt = ''.join(res.txts) if res.txts else ''
            # 去噪：只保留中文主体（去字母/数字/标点/空白）
            txt = ''.join(re.findall(r'[\u4e00-\u9fff，。！？]', txt))
            if cur is None or txt != cur[1]:
                if cur is not None:
                    seq.append(cur)
                cur = (t, txt)
            t += STEP_MS
        if cur is not None:
            seq.append(cur)
        cap.release()
        # 合并同文本段
        merged = []
        for start, txt in seq:
            if merged and merged[-1][1] == txt:
                continue
            merged.append((start, txt))
        result[f'{ep}_{s//60}m{s%60:02d}s'] = merged
        print(f'== {ep} {s//60}m{s%60:02d}s ==', flush=True)
        for start, txt in merged:
            if txt:
                print(f'   {start//1000//60}m{start//1000%60:02d}s.{start%1000//100}  {txt[:36]}', flush=True)

    with open(os.path.join(BASE, 'review', 'context_dense.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print('保存 review/context_dense.json')


if __name__ == '__main__':
    main()
