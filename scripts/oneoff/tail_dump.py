# -*- coding: utf-8 -*-
"""转储每集片尾段(≥21m)库条目, 检查 ED 期间叠加的正片台词是否入册。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
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
for ep in sorted(libs):
    rows = libs[ep]
    tail = [r for r in rows if r[0] >= 21 * 60]
    last = rows[-1] if rows else (0, '-', '-')
    out.append(f'=== {ep} 总 {len(rows)} 条, 末条 {last[1]}, ≥21m 共 {len(tail)} 条')
    for r in tail:
        out.append(f'   {r[1]:>7s}  {r[2]}')
txt = '\n'.join(out)
open(os.path.join(B, 'review', 'tail_dump.txt'), 'w', encoding='utf-8').write(txt)
print(f'写出 review/tail_dump.txt ({len(txt)} 字符)')
for ep in ('P25', 'P24'):
    print(f'\n--- {ep} 22m00s 以后 ---')
    for r in [x for x in libs[ep] if x[0] >= 22 * 60]:
        print(f'   {r[1]:>7s}  {r[2]}')
