# -*- coding: utf-8 -*-
"""顺序读全片, 定位参考图(已存的 960x540 jpg)在视频中的真实出现时间。

不跳帧、不用 cap.set, 逐帧 read 并下采样比对, 记录 MAD 最小的若干秒。
用法: python locate_frame.py "P20" "P20_24m30s.jpg" "P25" "P25_23m18s.jpg"
"""
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
    return None


def run(ep, refname):
    ref = cv2.imread(os.path.join(F, refname))
    if ref is None:
        print(f'{refname} 读取失败', flush=True)
        return
    r = small(ref)
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS)
    best = []          # (mad, 秒)
    n = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        n += 1
        if n % 2:      # 隔帧比对即可(≈12fps), 够定位到秒
            continue
        mad = float(np.abs(small(fr) - r).mean())
        sec = int(round(n / fps))
        best.append((mad, sec))
    cap.release()
    best.sort()
    print(f'\n[{ep}] 参考图 {refname}, 共比对 {len(best)} 帧 (fps={fps:.3f})')
    seen = set()
    shown = 0
    for mad, sec in best:
        if sec in seen:
            continue
        seen.add(sec)
        print(f'   MAD={mad:6.2f}  视频位置 {sec // 60}m{sec % 60:02d}s')
        shown += 1
        if shown >= 8:
            break


if __name__ == '__main__':
    for i in range(1, len(sys.argv), 2):
        run(sys.argv[i], sys.argv[i + 1])
