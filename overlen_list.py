# -*- coding: utf-8 -*-
"""列出时间戳越界的条目及其配图帧名(供视频定位)。"""
import json
import os
import re

import cv2

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle_clean')
fm = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
MAP = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])

dur = {}
for f in os.listdir(V):
    m = re.match(r'\[(P\d+)\]', f)
    if m and f.lower().endswith('.mp4'):
        cap = cv2.VideoCapture(os.path.join(V, f))
        dur[m.group(1)] = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
        cap.release()

lines, frames = [], []
for fn in sorted(os.listdir(CLEAN)):
    m = re.match(r'\[(P\d+)\]', fn)
    if not m:
        continue
    ep = m.group(1)
    d = dur[ep]
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        t = re.match(r'(\d+)m(\d+)s', e.get('timestamp') or '')
        if not t:
            continue
        sec = int(t.group(1)) * 60 + int(t.group(2))
        if sec <= d:
            continue
        cand = [v for k, v in MAP.items() if k.startswith(f'[{ep}]') and k.endswith('|' + e['timestamp'])]
        fr = cand[0] if cand else '(无)'
        lines.append(f'{ep}\t{e["timestamp"]}\t{sec}\t{fr}\t{e.get("text")}')
        frames.append(fr)

txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'overlen_list.txt'), 'w', encoding='utf-8').write(txt)
json.dump(frames, open(os.path.join(B, 'review', 'overlen_frames.json'), 'w', encoding='utf-8'),
          ensure_ascii=False)
print(f'越界条目 {len(lines)} 条, 涉及帧 {len(set(frames))} 个(去重)')
print(txt)
