# -*- coding: utf-8 -*-
"""一致性检查: 库条目时间戳是否超出视频实际长度(超出即为错误时间戳)。"""
import json
import os
import re

import cv2

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根(scripts/pipeline 的上三级)
B = _ROOT
V = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle')

dur = {}
for f in os.listdir(V):
    m = re.match(r'\[(P\d+)\]', f)
    if m and f.lower().endswith('.mp4'):
        cap = cv2.VideoCapture(os.path.join(V, f))
        n, fps = cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        dur[m.group(1)] = n / fps

lines, total, bad = ['库条目 vs 视频长度 一致性'], 0, 0
for fn in sorted(os.listdir(CLEAN)):
    # 只认 .json —— 之前的写法把落盘前的 .bak_qapply2 / .bak_outscope 备份也当库读了一遍,
    # 于是每集被统计两次(且两次条目数不同), 容易掩盖真问题
    if not fn.endswith('.json'):
        continue
    m = re.match(r'\[(P\d+)\]', fn)
    if not m:
        continue
    ep = m.group(1)
    rows = []
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        t = re.match(r'(\d+)m(\d+)s', e.get('timestamp') or '')
        if t:
            rows.append((int(t.group(1)) * 60 + int(t.group(2)), e['timestamp'], e.get('text')))
    total += len(rows)
    d = dur.get(ep, 0)
    over = [r for r in rows if r[0] > d]
    if over:
        bad += len(over)
        lines.append(f'  {ep} 视频长 {int(d) // 60}m{int(d) % 60:02d}s, 超长条目 {len(over)}:')
        for r in over:
            lines.append(f'      {r[1]:>7s}  {r[2][:40]}')
    last = max(r[0] for r in rows) if rows else 0
    lines.append(f'  {ep}: 条目 {len(rows)}, 末条 {last // 60}m{last % 60:02d}s, '
                 f'视频 {int(d) // 60}m{int(d) % 60:02d}s, 余量 {int(d) - last}s')
lines.insert(1, f'总条目 {total}, 超出视频长度的 {bad} 条')
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'duration_check.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
