# -*- coding: utf-8 -*-
"""顺序读视频, 抽取指定秒的画面存到 review/probe/, 供人工目视比对。"""
import os
import sys

import cv2

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
OUT = os.path.join(B, 'review', 'probe')


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def main():
    ep = sys.argv[1]
    secs = sorted({int(x) for x in sys.argv[2:]})
    os.makedirs(OUT, exist_ok=True)
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS)
    want = set(secs)
    n = 0
    got = {}
    while want:
        ok, fr = cap.read()
        if not ok:
            break
        n += 1
        sec = int(n / fps)
        if sec in want:
            got[sec] = fr
            want.discard(sec)
    cap.release()
    for sec, fr in sorted(got.items()):
        small = cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA)
        p = os.path.join(OUT, f'{ep}_{sec // 60}m{sec % 60:02d}s_video.jpg')
        cv2.imwrite(p, small, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print('写出', p)


if __name__ == '__main__':
    main()
