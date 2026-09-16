# -*- coding: utf-8 -*-
"""单次顺序读全片, 同时定位多张参考图在视频中的真实时间(用于刻画时间戳偏移)。"""
import os
import sys

import cv2
import numpy as np

V = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\Videos'
F = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\docs\frames'


def small(img):
    return cv2.cvtColor(cv2.resize(img, (240, 135)), cv2.COLOR_BGR2GRAY).astype(np.int16)


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def run(ep, refs):
    mats = []
    for r in refs:
        img = cv2.imread(os.path.join(F, r))
        mats.append((r, small(img)) if img is not None else None)
    mats = [x for x in mats if x]
    best = {r: [] for r, _ in mats}
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        n += 1
        if n % 2:
            continue
        sm = small(fr)
        sec = int(round(n / fps))
        for r, m in mats:
            best[r].append((float(np.abs(sm - m).mean()), sec))
    cap.release()
    print(f'\n[{ep}] fps={fps:.3f} 总帧≈{n}')
    for r, _ in mats:
        best[r].sort()
        seen, shown = set(), []
        for mad, sec in best[r]:
            if sec in seen:
                continue
            seen.add(sec)
            shown.append(f'{sec // 60}m{sec % 60:02d}s(MAD={mad:.1f})')
            if len(shown) >= 3:
                break
        print(f'  {r:18s} 最佳匹配: ' + '  '.join(shown))


if __name__ == '__main__':
    ep = sys.argv[1]
    run(ep, sys.argv[2:])
