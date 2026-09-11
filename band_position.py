# -*- coding: utf-8 -*-
"""测量指定帧中"近白文字像素"的纵向分布, 判断字幕是否落在 SUBTITLE_AREA 之外。

输出: 每帧按行统计近白像素数, 给出文字行带的 y 区间(换算到 1920x1080 坐标),
      并标注当前字幕带 (100,895,1820,985) 是否覆盖。
"""
import os

import cv2
import numpy as np

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'Web', 'frames')
BAND = (895, 985)
TARGETS = [('P21_24m10s.jpg', '资料卡中文字幕'), ('P21_24m15s.jpg', '正常对白(对照)'),
           ('P22_3m52s.jpg', '次回预告卡'), ('P18_0m56s.jpg', '新闻画面'),
           ('P01_22m53s.jpg', '片尾歌词')]

lines = [f'当前字幕带 y = {BAND[0]}~{BAND[1]} (1920x1080 坐标)', '']
for f, note in TARGETS:
    img = cv2.imread(os.path.join(FR, f))
    if img is None:
        lines.append(f'{f}: 读图失败')
        continue
    h, w = img.shape[:2]
    sy = 1080.0 / h
    b, g, r = img[:, :, 0].astype(np.int16), img[:, :, 1].astype(np.int16), img[:, :, 2].astype(np.int16)
    mask = (np.minimum(np.minimum(b, g), r) > 225)
    prof = mask.sum(axis=1)
    thr = max(3, int(prof.max() * 0.06))
    bands, start = [], None
    for y, v in enumerate(prof):
        if v >= thr and start is None:
            start = y
        elif v < thr and start is not None:
            bands.append((start, y - 1))
            start = None
    if start is not None:
        bands.append((start, h - 1))
    yy = [(round(a * sy), round(b2 * sy), int(prof[a:b2 + 1].max())) for a, b2 in bands]
    inside = [t for t in yy if not (t[1] < BAND[0] or t[0] > BAND[1])]
    lines.append(f'{f} ({note}) 文字行带 y(1080p)={yy}')
    lines.append(f'    落进字幕带的行带: {inside if inside else "无"}')
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'band_position.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
