# -*- coding: utf-8 -*-
"""q_speed2.py — 验证"跳过检测、只跑识别(rec)"的可行性与加速比。

本项目的裁剪已经是"按文字行切好的单行带", 不需要 det 再找框; 直接调 text_rec 可省一次检测前向。
用法: python q_speed2.py
"""
import os
import time

import cv2
import numpy as np

from q_common import (SCAN_TOP, SCAN_BOT, X0, X1, PAD_Y, build_engine, crop_norm,
                      gray_white, split_lines)

B = os.path.dirname(os.path.abspath(__file__))
vid = os.path.join(B, 'Videos', '[P01]1 罗布奥特曼登场.mp4')
from rapidocr.ch_ppocr_rec.typings import TextRecInput  # noqa: E402

cap = cv2.VideoCapture(vid)
for _ in range(2000):
    cap.grab()
ret, frame = cap.read()
cap.release()

segs = [s for s in split_lines(frame, SCAN_TOP, SCAN_BOT) if s[1] - s[0] >= 20]
print('有效段', segs)
ocr = build_engine()
print('engine ready, rec_img_shape=', ocr.text_rec.rec_image_shape)


def tight_x(img, y0, y1, pad=12):
    """按列投影裁到文字实际水平范围 —— 减少 rec 输入宽度, 直接决定耗时。"""
    sy = img.shape[0] / 1080.0
    sx = img.shape[1] / 1920.0
    sub = gray_white(img[max(0, int((y0 - 2) * sy)):int((y1 + 2) * sy),
                         int(X0 * sx):int(X1 * sx)])
    cols = sub.sum(axis=0)
    nz = np.where(cols > 0)[0]
    if len(nz) == 0:
        return None
    x0 = max(X0, int(X0 + (nz[0] - pad) / sx))
    x1 = min(X1, int(X0 + (nz[-1] + pad) / sx))
    return x0, x1


for tag, s in (('seg', segs[0]),):
    crop = crop_norm(frame, (X0, s[0] - PAD_Y, X1, s[1] + PAD_Y), upscale=1.0)
    print('crop', crop.shape)
    t0 = time.time()
    r_full = ocr(crop)
    t_full = time.time() - t0
    t0 = time.time()
    r_rec = ocr.text_rec(TextRecInput(img=crop))
    t_rec = time.time() - t0
    tx = tight_x(frame, s[0], s[1])
    crop2 = crop_norm(frame, (tx[0], s[0] - PAD_Y, tx[1], s[1] + PAD_Y), upscale=1.0)
    t0 = time.time()
    r_rec2 = ocr.text_rec(TextRecInput(img=crop2))
    t_tight = time.time() - t0
    t0 = time.time()
    r_full2 = ocr(crop2)
    t_full2 = time.time() - t0
    print(f'全流程   {t_full:.3f}s -> {r_full.txts}')
    print(f'仅rec    {t_rec:.3f}s -> {r_rec.txts} scores={r_rec.scores}')
    print(f'紧裁形状 {crop2.shape} (x {tx})')
    print(f'紧裁仅rec {t_tight:.3f}s -> {r_rec2.txts}')
    print(f'紧裁全流程 {t_full2:.3f}s -> {r_full2.txts}')

# 二次热行, 排除首帧抖动
for tag, fn in (('仅rec', lambda: ocr.text_rec(TextRecInput(img=crop))),
                ('全流程', lambda: ocr(crop)),
                ('紧裁仅rec', lambda: ocr.text_rec(TextRecInput(img=crop2)))):
    t0 = time.time()
    for _ in range(5):
        fn()
    print(f'{tag} x5: {(time.time() - t0) / 5:.3f}s/次')
