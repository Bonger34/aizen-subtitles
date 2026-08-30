# -*- coding: utf-8 -*-
"""scan6_probe.py — 针对指定正常句的扩窗多通道探测"""
import json
import os
import re
import sys

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
SUBTITLE_AREA = (100, 895, 1820, 985)
W, H = 960, 540
MATCH_MIN = 0.5
QUOTE_RE = re.compile(r'[“”‘’"\']')
TARGETS = [
    ('[P25]25 朝阳之家', '19m14s', '真是不可思议'),
    ('[P25]25 朝阳之家', '23m29s', '变得更加强大'),
]


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def ts_str(sec):
    sec = int(round(sec))
    return f'{sec // 60}m{sec % 60:02d}s'


def lcs(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i][j - 1], dp[i - 1][j])
    return dp[m][n]


def ratio(a, b):
    return lcs(a, b) / min(len(a), len(b)) if a and b else 0


def main():
    ocr = RapidOCR()
    video = [f for f in os.listdir(os.path.join(BASE, 'Videos'))
             if f.startswith('[P25]') and f.endswith('.mp4')][0]
    cap = cv2.VideoCapture(os.path.join(BASE, 'Videos', video))
    for _, ts, lib in TARGETS:
        sec = parse_ts(ts)
        best = None
        t0 = sec * 1000 - 3000
        t1 = sec * 1000 + 6000
        cap.set(cv2.CAP_PROP_POS_MSEC, int(t0))
        t = t0
        while t <= t1:
            ret, frame = cap.read()
            if frame is None:
                break
            # 通道1 全帧
            res, _ = ocr(frame)
            ta = ''.join(x[1] for x in res) if res else ''
            # 通道2 字幕带 bin
            crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            _, b = cv2.threshold(255 - gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            res2, _ = ocr(cv2.cvtColor(b, cv2.COLOR_GRAY2BGR))
            tb = ''.join(x[1] for x in res2) if res2 else ''
            for txt in (ta, tb):
                c = QUOTE_RE.sub('', txt).replace(' ', '')
                lc = QUOTE_RE.sub('', lib).replace(' ', '')
                r = ratio(lc, c) if c else 0
                if r >= MATCH_MIN and (best is None or r > best[0]):
                    best = (r, frame.copy(), t, txt)
            t += 250
        if best is not None:
            name = f'P25_{ts_str(best[2] / 1000)}.jpg'
            cv2.imwrite(os.path.join(BASE, 'web', 'frames', name),
                        cv2.resize(best[1], (W, H)), [cv2.IMWRITE_JPEG_QUALITY, 82])
            print(f'HIT {ts} [{lib}] -> {name} ratio {best[0]:.2f} text={best[3][:30]!r}', flush=True)
        else:
            print(f'MISS {ts} [{lib}]', flush=True)
    cap.release()


if __name__ == '__main__':
    main()
