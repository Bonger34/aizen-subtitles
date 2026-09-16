# -*- coding: utf-8 -*-
"""probe_frames.py — 连续读帧, 输出指定帧区间每 5 帧的字幕带, 供人工核对序列
用法: python probe_frames.py [视频] [起始fidx] [结束fidx] [步长]
"""
import os
import sys

import cv2

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
AREA = (100, 895, 1820, 985)


def main():
    ep_video, s0, e0, step = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 5
    video = os.path.join(BASE, 'Videos', ep_video)
    cap = cv2.VideoCapture(video)
    out = os.path.join(BASE, 'review', 'probe_frames')
    os.makedirs(out, exist_ok=True)
    fidx = 0
    saved = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if s0 <= fidx <= e0 and (fidx - s0) % step == 0:
            crop = frame[AREA[1]:AREA[3], AREA[0]:AREA[2]]
            fn = os.path.join(out, f'f{fidx}.jpg')
            cv2.imwrite(fn, crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
            saved.append(fn)
        fidx += 1
    cap.release()
    print('\n'.join(saved), flush=True)


if __name__ == '__main__':
    main()
