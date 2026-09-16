# -*- coding: utf-8 -*-
"""查看指定集在指定秒附近的库条目, 判断孤儿帧是否是唯一证据。"""
import json
import os
import re
import sys

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
TARGETS = [('P10', 10 * 60 + 59), ('P20', 24 * 60 + 30), ('P04', 1 * 60 + 55),
           ('P16', 2 * 60 + 27), ('P01', 5 * 60 + 36), ('P08', 3 * 60 + 35),
           ('P18', 1 * 60 + 14), ('P25', 21 * 60 + 23), ('P22', 4 * 60 + 45)]

libs = {}
for fn in os.listdir(CLEAN):
    m = re.match(r'\[(P\d+)\]', fn)
    if not m:
        continue
    rows = []
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        mm = re.match(r'(\d+)m(\d+)s', e.get('timestamp') or '')
        if mm:
            rows.append((int(mm.group(1)) * 60 + int(mm.group(2)), e['timestamp'], e.get('text')))
    libs[m.group(1)] = sorted(rows)

out = []
for ep, sec in TARGETS:
    rows = libs.get(ep, [])
    near = [r for r in rows if abs(r[0] - sec) <= 12]
    out.append(f'--- {ep} @ {sec // 60}m{sec % 60:02d}s  库内总 {len(rows)} 条, ±12s 内 {len(near)} 条')
    for r in near:
        out.append(f'      {r[1]:>7s}  {r[2]}')
    if not near:
        # 显示前后最近的条目, 判断是否真的空档
        before = [r for r in rows if r[0] < sec][-3:]
        after = [r for r in rows if r[0] > sec][:3]
        out.append('      (空档) 前:' + ' | '.join(f'{r[1]} {r[2]}' for r in before))
        out.append('             后:' + ' | '.join(f'{r[1]} {r[2]}' for r in after))
txt = '\n'.join(out)
open(os.path.join(B, 'review', 'orphan_ctx.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
