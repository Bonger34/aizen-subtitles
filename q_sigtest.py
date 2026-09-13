# -*- coding: utf-8 -*-
"""q_sigtest.py — 校准字幕签名: 对比"先缩放后阈值"与"先阈值后缩放"的白像素保留情况。
用法: python q_sigtest.py P02 14 24 [step秒]
"""
import os
import sys

import cv2
import numpy as np

B = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(B, 'Videos')
BAND = (840, 1080)
SIG_SZ = (192, 24)


def sig_old(frame):
    c = frame[BAND[0]:BAND[1]]
    g = cv2.cvtColor(cv2.resize(c, SIG_SZ, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    return (g > 235).astype(np.uint8)


def sig_new(frame, ratio=0.15, white=235):
    """先判断近白(三通道最小值>阈值)再缩放 -> 用白像素占比再二值化, 细笔画不会因平均而消失。"""
    c = frame[BAND[0]:BAND[1]]
    m = (np.minimum(np.minimum(c[:, :, 0], c[:, :, 1]), c[:, :, 2]) > white).astype(np.float32)
    s = cv2.resize(m, SIG_SZ, interpolation=cv2.INTER_AREA)
    return (s > ratio).astype(np.uint8)


def main():
    ep, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    step = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = 0
    t = t0
    prev_o = prev_nw = None
    while t <= t1:
        fno = int(round(t * fps))
        while n < fno:
            cap.grab()
            n += 1
        ok, f = cap.read()
        n += 1
        if not ok:
            break
        so, sn = sig_old(f), sig_new(f)
        do = dn = -1.0
        if prev_o is not None:
            do = float(np.abs(so.astype(np.int16) - prev_o.astype(np.int16)).mean())
            dn = float(np.abs(sn.astype(np.int16) - prev_nw.astype(np.int16)).mean())
        print(f'  t{t:>6.2f} 旧签名 white={int(so.sum()):>5d} diff={do:.4f} | '
              f'新签名 white={int(sn.sum()):>5d} diff={dn:.4f}')
        prev_o, prev_nw = so, sn
        t += step
    cap.release()


if __name__ == '__main__':
    main()
