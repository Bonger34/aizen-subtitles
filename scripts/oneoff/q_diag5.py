# -*- coding: utf-8 -*-
"""q_diag5.py — 打印 1080p 帧扫描区的逐行白像素剖面 + 扫描 row_th_ratio。

用法: python q_diag5.py P01 537.81
目的: 弄清"白衬衫把字幕行连成一大段"的具体剖面形态, 找到能切开的阈值。
"""
import os
import sys

import cv2
import numpy as np

import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import SCAN_TOP, SCAN_BOT, WHITE_MIN, build_engine, gray_white, split_lines
from q_rescan import rec_pair, tight_x

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(B, 'Videos')

ep, t = sys.argv[1], float(sys.argv[2])
thr_white = int(sys.argv[3]) if len(sys.argv) > 3 else WHITE_MIN
vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
       if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
cap = cv2.VideoCapture(vid)
fps = cap.get(cv2.CAP_PROP_FPS)
fno = int(round(t * fps))
n = 0
while n < fno:
    cap.grab()
    n += 1
ok, frame = cap.read()
cap.release()
print(f'{ep} t={t}s fno={fno} ok={ok} shape={frame.shape} 白阈值={thr_white}')

# --- 逐行剖面: 每 5 行打印一次 y / 白像素数 / 占宽比例
mask = gray_white(frame, thr_white)
prof = mask.sum(axis=1)
W = frame.shape[1]
print(f'\n行剖面 (扫描区 y{SCAN_TOP}-{SCAN_BOT}, 峰值={prof[SCAN_TOP:SCAN_BOT].max()}, 宽={W}):')
for y in range(SCAN_TOP, min(SCAN_BOT, frame.shape[0]), 5):
    c = int(prof[y])
    bar = '#' * min(60, int(c / max(1, W) * 60))
    print(f'  y{y:4d} {c:5d} {c / W:5.3f} {bar}')

ocr = build_engine()
from rapidocr.ch_ppocr_rec.typings import TextRecInput
ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))

print('\n=== row_th_ratio 扫描 ===')
for ratio in (0.12, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
    segs = split_lines(frame, SCAN_TOP, SCAN_BOT, row_th_ratio=ratio, white_min=thr_white)
    out = []
    for y0, y1, fill in sorted(segs, key=lambda s: -s[2])[:4]:
        tx = tight_x(frame, y0, y1)
        txt = ''
        if tx:
            rr = rec_pair(ocr, frame, y0, y1, tx, ('bin',))
            txt = rr.get('bin') or ''
        out.append(f'y{y0}-{y1} h{y1 - y0} fill={fill} -> [{txt}]')
    print(f'\n ratio={ratio}: {len(segs)} 段')
    for line in out:
        print(f'    {line}')
