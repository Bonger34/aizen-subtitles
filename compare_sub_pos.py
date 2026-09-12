# -*- coding: utf-8 -*-
"""对比"库中已有的台词"与"漏掉的台词"在画面中的纵向位置。"""
import os
import sys

import cv2
import numpy as np

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
CASES = [('P22', 16 * 60 + 46, '库中有: 这次就包在我们身上吧'),
         ('P22', 16 * 60 + 47, '库中有: 朝阳你先回家'),
         ('P22', 16 * 60 + 6, '漏掉: 休想得逞'),
         ('P22', 16 * 60 + 50, '漏掉: 勇海我们上'),
         ('P24', 17 * 60 + 10, '库中有: 将牵引光束对准鲁格赛特'),
         ('P24', 17 * 60 + 14, '漏掉: 明白发射牵引光束'),
         ('P24', 18 * 60 + 2, '库中有: 这是最后的水晶了')]


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


for ep, s, note in CASES:
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(s * fps)))
    ok, fr = cap.read()
    cap.release()
    if not ok:
        print(f'{ep} {s}: 失败')
        continue
    h, w = fr.shape[:2]
    sy = 1080.0 / h
    gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    prof = (gray > 245).sum(axis=1)
    thr = max(4, int(prof.max() * 0.25))
    runs = []
    for y in range(h):
        if prof[y] >= thr and y * sy > 700:
            if runs and y - runs[-1][1] <= 4:
                runs[-1][1] = y
            else:
                runs.append([y, y])
    bands = [(round(a * sy), round(b * sy)) for a, b in runs if (b - a) >= 4]
    inband = [b for b in bands if not (b[1] < 895 or b[0] > 985)]
    print(f'{ep} {s // 60}m{s % 60:02d}s  {note}')
    print(f'    下三分之一文字行带(1080p)={bands}  落在字幕带内的={inband}')
