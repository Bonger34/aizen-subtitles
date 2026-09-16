# -*- coding: utf-8 -*-
"""把 9 条未解决目标"自己那一秒"的画面抓到 review/probe/ 供目视(seek + 读帧, 内容不验证)。"""
import json
import os
import re

import cv2

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
OUT = os.path.join(B, 'review', 'probe')
os.makedirs(OUT, exist_ok=True)
prog = json.load(open(os.path.join(B, 'review', 'shared_fix3_progress.json'), encoding='utf-8'))
todo = [v for v in prog.values() if (v.get('score') or 0) < 0.8]


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


for v in todo:
    ep, ts = v['ep'], v['ts']
    sec = int(ts.split('m')[0]) * 60 + int(ts.split('m')[1].rstrip('s'))
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(sec * fps)))
    ok, fr = cap.read()
    cap.release()
    if not ok:
        print(f'{ep} {ts}: 读帧失败')
        continue
    p = os.path.join(OUT, f'res_{ep}_{ts}.jpg')
    cv2.imwrite(p, cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"{ep} {ts}  库文本=[{v['text']}]  -> {p}")
