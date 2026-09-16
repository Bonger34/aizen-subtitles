# -*- coding: utf-8 -*-
"""dump_p03_7m12s.py — 导出 P03 7m12s 前后画面帧供人工核定

导出 430.0s ~ 442.0s 每 0.2s 一帧：
  review/p03_7m12s_frames/  61 张全帧 jpg（帧名含时刻）
  review/p03_7m12s_frames/index.md  每帧 rapidocr 字幕文本索引
  review/p03_7m12s_contact.png  拼图总览（照片墙 + 时间 + OCR）
"""
import os
import re

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO = os.path.join(BASE, 'Videos', '[P03]3 欢迎来到爱染科技.mp4')
OUT = os.path.join(BASE, 'review', 'p03_7m12s_frames')
SUBTITLE_AREA = (100, 895, 1820, 985)
W, H = 960, 540
T0 = 430.0
T1 = 442.0
STEP = 0.2
COLS = 6
THUMB_W, THUMB_H = 300, 169
LABEL_H = 26


def ts_str(sec):
    sec = int(round(sec))
    return f'{sec // 60}m{sec % 60:02d}s'


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith('.jpg') or f.endswith('.md'):
            os.remove(os.path.join(OUT, f))
    ocr = RapidOCR()
    print('OCR 就绪', flush=True)
    cap = cv2.VideoCapture(VIDEO)

    # 1) 逐帧保存 + OCR 索引
    rows = []   # (sec, file, text)
    t = T0
    cap.set(cv2.CAP_PROP_POS_MSEC, int(T0 * 1000))
    while t <= T1 + 1e-6:
        ret, frame = cap.read()
        if frame is None:
            break
        name = f'{ts_str(t)}_{int(round(t * 10)) % 10}.jpg'  # 含帧内 0.1 位
        cv2.imwrite(os.path.join(OUT, name),
                    cv2.resize(frame, (W, H)), [cv2.IMWRITE_JPEG_QUALITY, 85])
        crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
        res, _ = ocr(crop)
        txt = ''.join(x[1] for x in res) if res else ''
        rows.append((round(t, 1), name, txt))
        t += STEP
    cap.release()
    print(f'导出 {len(rows)} 帧', flush=True)

    # 2) index.md
    with open(os.path.join(OUT, 'index.md'), 'w', encoding='utf-8') as fh:
        fh.write('# P03 7m12s 前后画面帧（430s-442s，0.2s 间隔）\n\n')
        fh.write('库文本待核定：**该句在画面中是否出现过**\n\n')
        fh.write('| 时刻 | 文件 | 字幕 OCR |\n|---|---|---|\n')
        for sec, name, txt in rows:
            fh.write(f'| {ts_str(sec)} | {name} | {txt or "(无字幕)"} |\n')

    # 3) contact sheet 拼图
    n = len(rows)
    rows_n = (n + COLS - 1) // COLS
    sheet = np.full((rows_n * (THUMB_H + LABEL_H), COLS * THUMB_W, 3), 245,
                    dtype=np.uint8)
    for i, (sec, name, txt) in enumerate(rows):
        img = cv2.imread(os.path.join(OUT, name))
        img = cv2.resize(img, (THUMB_W, THUMB_H))
        r0 = (i // COLS) * (THUMB_H + LABEL_H)
        c0 = (i % COLS) * THUMB_W
        sheet[r0:r0 + THUMB_H, c0:c0 + THUMB_W] = img
        label = f'{ts_str(sec)}  {txt[:18] or "-"}'
        cv2.rectangle(sheet, (c0, r0 + THUMB_H), (c0 + THUMB_W, r0 + THUMB_H + LABEL_H), (255, 255, 255), -1)
        cv2.putText(sheet, label, (c0 + 6, r0 + THUMB_H + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (30, 60, 120), 1, cv2.LINE_AA)
        if txt:
            cv2.rectangle(sheet, (c0, r0), (c0 + THUMB_W, r0 + THUMB_H), (0, 200, 0), 2)
    cv2.imwrite(os.path.join(BASE, 'review', 'p03_7m12s_contact.png'), sheet)
    print(f'完成: {OUT} ({n} 帧) + contact sheet')


if __name__ == '__main__':
    main()
