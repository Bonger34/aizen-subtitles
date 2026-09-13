# -*- coding: utf-8 -*-
"""q_prof2.py — rec 调用开销基准: 单张 vs 批量(rec_batch_num), 决定重扫是否需要攒批。
用法: python q_prof2.py
"""
import os
import time

import cv2
import numpy as np

from q_common import build_engine
from rapidocr.ch_ppocr_rec.typings import TextRecInput

B = os.path.dirname(os.path.abspath(__file__))
vid = os.path.join(B, 'Videos', '[P01]1 罗布奥特曼登场.mp4')
cap = cv2.VideoCapture(vid)
for _ in range(15000):
    cap.grab()
ok, frame = cap.read()
cap.release()


def mk(h, w):
    """造一张"白底黑字"条带图, 模拟紧裁后的字幕裁剪。"""
    img = np.zeros((h, w, 3), np.uint8)
    for i in range(0, w - 40, 60):
        cv2.putText(img, '测', (i + 5, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    return img


ocr = build_engine()
print('rec_batch_num =', ocr.text_rec.rec_batch_num)

# 预热
ocr.text_rec(TextRecInput(img=mk(72, 600)))
for size in ((72, 600), (176, 1200), (246, 1840), (52, 300)):
    img = mk(*size)
    n = 30
    t0 = time.time()
    for _ in range(n):
        ocr.text_rec(TextRecInput(img=img))
    t1 = (time.time() - t0) / n
    t0 = time.time()
    for _ in range(n // 5):
        ocr.text_rec(TextRecInput(img=[img] * 5))
    t5 = (time.time() - t0) / (n // 5) / 5
    t0 = time.time()
    for _ in range(n // 10):
        ocr.text_rec(TextRecInput(img=[img] * 10))
    t10 = (time.time() - t0) / (n // 10) / 10
    print(f'size {size}: 单张 {t1 * 1000:.0f}ms | 批5 {t5 * 1000:.0f}ms/张 | 批10 {t10 * 1000:.0f}ms/张')

# 混合尺寸批(真实场景: 一集内各段尺寸不同)
imgs = [mk(72, 600), mk(60, 900), mk(176, 1200), mk(52, 320), mk(90, 700), mk(70, 500)]
t0 = time.time()
for _ in range(20):
    ocr.text_rec(TextRecInput(img=imgs))
print(f'混合尺寸批6 {((time.time() - t0) / 20 / 6) * 1000:.0f}ms/张')
