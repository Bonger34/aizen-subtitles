# -*- coding: utf-8 -*-
"""q_prof3.py — 测 rec_batch_num 对批处理吞吐的影响(单张 46ms 是固定启动开销, 攒批也许能摊薄)。
用法: python q_prof3.py
"""
import time

import cv2
import numpy as np

from q_common import build_engine
from rapidocr.ch_ppocr_rec.typings import TextRecInput


def mk(h, w):
    img = np.zeros((h, w, 3), np.uint8)
    for i in range(0, w - 40, 60):
        cv2.putText(img, '测', (i + 5, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    return img


for bn in (1, 6):
    ocr = build_engine(rec_batch_num=bn)
    print(f'--- rec_batch_num={bn} (生效值 {ocr.text_rec.rec_batch_num})')
    img = mk(72, 600)
    ocr.text_rec(TextRecInput(img=img))
    t0 = time.time()
    for _ in range(30):
        ocr.text_rec(TextRecInput(img=img))
    print(f'  单张 {(time.time() - t0) / 30 * 1000:.1f}ms')
    if bn > 1:
        for k in (bn, bn * 2):
            imgs = [mk(60 + 6 * i, 400 + 90 * i) for i in range(k)]
            t0 = time.time()
            for _ in range(10):
                ocr.text_rec(TextRecInput(img=imgs))
            print(f'  批{k} {(time.time() - t0) / 10 / k * 1000:.1f}ms/张')
