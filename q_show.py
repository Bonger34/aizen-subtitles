# -*- coding: utf-8 -*-
"""q_show.py — 把指定时间区间的视频帧按固定间隔裁出字幕带并拼图, 用于肉眼核对字幕与白像素。

用法: python q_show.py P02 14 24 [间隔秒=0.5] [带宽=300]
输出: review/q_show_<EP>_<t0>_<t1>.jpg
"""
import os
import sys

import cv2
import numpy as np

B = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(B, 'Videos')


def main():
    ep, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    step = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
    top = int(sys.argv[5]) if len(sys.argv) > 5 else 300
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    n = 0
    t = t0
    while t <= t1:
        fno = int(round(t * fps))
        while n < fno:
            cap.grab()
            n += 1
        ok, f = cap.read()
        n += 1
        if not ok:
            break
        y0 = 1080 - top
        band = f[y0:1080]
        white = int((cv2.cvtColor(band, cv2.COLOR_BGR2GRAY) > 235).sum())
        band = cv2.resize(band, (1500, int(top * 1500 / 1920)))
        cv2.putText(band, f't{t:.2f} white235={white}', (8, 26), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 0, 255), 2)
        rows.append(band)
        print(f'  t{t:.2f} white235={white}')
        t += step
    cap.release()
    if rows:
        out = os.path.join(B, 'review', f'q_show_{ep}_{t0:g}_{t1:g}.jpg')
        cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 92])
        print('saved', out)


if __name__ == '__main__':
    main()
