# -*- coding: utf-8 -*-
"""廉价判定(不做 OCR): ±120s 窗口内逐帧检测字幕区间, 检查是否都被库中其他条目覆盖。

若窗口内所有字幕区间都已有序目覆盖, 说明该条目在那一刻并无对应字幕(条目为 OCR 噪声)。
"""
import json
import os
import re

import cv2

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle_clean')
TARGETS = [('P22', '17m53s'), ('P24', '18m11s')]
WIN = 120
BAND = (100, 895, 1820, 985)
ON_TH, OFF_TH = 0.02, 0.01


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


for ep, ts in TARGETS:
    base = sec_of(ts)
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    lib = sorted(sec_of(e['timestamp']) for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')))
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    lo, hi = max(0, base - WIN), base + WIN
    start_f, end_f = int(lo * fps), min(total - 1, int(hi * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)
    ivs, state, s0, n = [], 'off', None, start_f
    while n <= end_f:
        ok, fr = cap.read()
        if not ok:
            break
        n += 1
        g = cv2.cvtColor(fr[BAND[1]:BAND[3], BAND[0]:BAND[2]], cv2.COLOR_BGR2GRAY)
        wr = float((g > 245).mean())
        sec = n / fps
        if state == 'off':
            if wr > ON_TH:
                state, s0 = 'on', sec
        elif wr < OFF_TH:
            ivs.append((round(s0, 1), round(sec, 1)))
            state = 'off'
    if state == 'on':
        ivs.append((round(s0, 1), round(n / fps, 1)))
    cap.release()
    print(f'=== {ep} {ts}  窗口 {lo // 60}m{lo % 60:02d}s~{hi // 60}m{hi % 60:02d}s  区间 {len(ivs)} 段')
    uncov = []
    for a, b in ivs:
        mid = (a + b) / 2
        near = [x for x in lib if a - 2 <= x <= b + 2]
        flag = '' if near else '   <== 无库条目覆盖'
        if not near:
            uncov.append((a, b))
        print(f'   [{int(a) // 60:02d}m{a % 60:05.2f}s - {int(b) // 60:02d}m{b % 60:05.2f}s] 时长{b - a:5.2f}s '
              f'库内近邻={near[:3]}{flag}')
    print(f'   --> 未被覆盖的区间: {len(uncov)} 段 {uncov}')
    print()
