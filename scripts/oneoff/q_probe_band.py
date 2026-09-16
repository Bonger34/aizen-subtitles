# -*- coding: utf-8 -*-
"""q_probe_band.py — 探针: 找出能在 1080p 帧里把"字幕行"与"大面积白色衣物"分开的判据。

背景: 白衬衫让 y840-1075 的白像素剖面几乎平坦(130~275/1920), 行阈值法无论取多少都会
把整片连成一段, OCR 读不出。字幕行真实位置固定在人脸下方 y≈895~1000(见 review/band_position.txt)。

本脚本对给定帧打印三种掩膜的逐行剖面, 看哪种能把 y895~1000 单独凸显出来:
  A 白掩膜(基线)
  B 黑描边掩膜: 暗像素 且 邻域存在白像素(字幕字形有黑描边, 衬衫/夹克没有)
  C 白描边掩膜: 白像素 且 邻域存在暗像素

用法: python q_probe_band.py P01 537.81 [P01 642.0 ...]
"""
import os
import sys

import cv2
import numpy as np

import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import SCAN_TOP, SCAN_BOT

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(B, 'Videos')
W_THR, D_THR = 200, 90


def read_at(ep, t):
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    n, fno = 0, int(round(t * fps))
    while n < fno:
        cap.grab()
        n += 1
    ok, fr = cap.read()
    cap.release()
    return fr


def masks(img):
    mn, mx = img.min(axis=2), img.max(axis=2)
    white = mn > W_THR
    dark = mx < D_THR
    k = np.ones((9, 9), np.uint8)
    near_w = cv2.dilate(white.astype(np.uint8), k) > 0
    near_d = cv2.dilate(dark.astype(np.uint8), k) > 0
    return {'A白': white, 'B黑描边': dark & near_w, 'C白带黑边': white & near_d}


def main():
    for i in range(1, len(sys.argv), 2):
        ep, t = sys.argv[i], float(sys.argv[i + 1])
        fr = read_at(ep, t)
        if fr is None:
            print(f'{ep} {t}: 读帧失败')
            continue
        print(f'\n===== {ep} t={t}s =====')
        cols = {}
        for name, m in masks(fr).items():
            prof = m.sum(axis=1)
            cols[name] = prof
            seg = prof[SCAN_TOP:SCAN_BOT]
            peak = int(seg.max())
            i0 = SCAN_TOP + int(seg.argmax())
            print(f'  {name}: 峰值={peak}@y{i0} 均值={seg.mean():.0f}')
        print('   y      ' + '  '.join(f'{k:>9s}' for k in cols))
        for y in range(SCAN_TOP, min(SCAN_BOT, fr.shape[0]), 5):
            row = '  '.join(f'{int(cols[k][y]):9d}' for k in cols)
            print(f'  y{y:4d}  {row}')
        # 各掩膜按 60% 峰值切出的行段
        for name, prof in cols.items():
            seg = prof[SCAN_TOP:SCAN_BOT]
            thr = max(3, int(seg.max() * 0.6))
            ys = np.where(prof[SCAN_TOP:SCAN_BOT] >= thr)[0]
            runs = []
            for y in ys:
                if runs and y - runs[-1][1] <= 2:
                    runs[-1][1] = y
                else:
                    runs.append([y, y])
            rs = [(SCAN_TOP + a, SCAN_TOP + b) for a, b in runs if b - a >= 3]
            print(f'  {name} 0.6峰值行段: {rs}')


if __name__ == '__main__':
    main()
