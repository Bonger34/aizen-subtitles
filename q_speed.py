# -*- coding: utf-8 -*-
"""q_speed.py — 测速: 视频 grab 速度 / 裁剪 OCR 单次耗时, 用于估算全量重扫时间。"""
import os
import time

import cv2

from q_common import build_engine, crop_norm, ocr_text, split_lines, SCAN_TOP, SCAN_BOT, X0, X1, PAD_Y

B = os.path.dirname(os.path.abspath(__file__))
vid = os.path.join(B, 'Videos', '[P01]1 罗布奥特曼登场.mp4')

cap = cv2.VideoCapture(vid)
t0 = time.time()
n = 0
while n < 5000:
    if not cap.grab():
        break
    n += 1
t_grab = time.time() - t0
print(f'grab {n} 帧耗时 {t_grab:.2f}s -> {n / t_grab:.0f} fps, 全片 35284 帧约 {35284 / (n / t_grab):.1f}s')

ret, frame = cap.read()
cap.release()
print('frame', frame.shape)

t0 = time.time()
for _ in range(20):
    segs = split_lines(frame, SCAN_TOP, SCAN_BOT)
print(f'split_lines x20 耗时 {time.time() - t0:.4f}s, 段数 {len(segs)}')
for s in segs:
    print('   seg', s)

ocr = build_engine()
print('engine ready')
for s in segs[:3]:
    crop = crop_norm(frame, (X0, s[0] - PAD_Y, X1, s[1] + PAD_Y), upscale=1.0)
    for tag in ('cold', 'warm1', 'warm2'):
        t0 = time.time()
        txt = ocr_text(ocr, crop)
        print(f'   {tag} y{s[0]}-{s[1]} OCR {time.time() - t0:.3f}s -> [{txt}]')
