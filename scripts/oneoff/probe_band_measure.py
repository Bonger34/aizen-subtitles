# -*- coding: utf-8 -*-
"""测量指定帧的文字行位置与"字幕带内白像素比", 判断为何字幕带没触发。"""
import os

import cv2
import numpy as np

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
P = os.path.join(B, 'review', 'probe')
FILES = ['P18_8m19s_video.jpg', 'P18_8m21s_video.jpg', 'P18_8m23s_video.jpg',
         'P18_9m31s_video.jpg', 'P11_10m11s_video.jpg']
BAND = (895, 985)

for f in FILES:
    img = cv2.imread(os.path.join(P, f))
    if img is None:
        print(f'{f}: 无此文件')
        continue
    h, w = img.shape[:2]
    sy = 1080.0 / h
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    prof = (gray > 225).sum(axis=1)
    thr = max(3, int(prof.max() * 0.25))
    runs = []
    for y in range(h):
        if prof[y] >= thr:
            if runs and y - runs[-1][1] <= 3:
                runs[-1][1] = y
            else:
                runs.append([y, y])
    bands = [(round(a * sy), round(b * sy)) for a, b in runs if (b - a) >= 3]
    bandmask = (gray[int(BAND[0] / sy):int(BAND[1] / sy), :] > 245)
    r245 = float(bandmask.mean())
    bandmask225 = (gray[int(BAND[0] / sy):int(BAND[1] / sy), :] > 225)
    print(f'{f}: 文字行带(1080p)={bands}')
    print(f'    字幕带 y895-985 内  >245 占比={r245:.4f}   >225 占比={float(bandmask225.mean()):.4f}'
          f'   (触发阈值 ON=0.02)')
