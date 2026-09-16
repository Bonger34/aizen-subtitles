# -*- coding: utf-8 -*-
"""查询指定集指定区间的库条目及其 map 配图, 用于核对'条目配图是否正确'。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
fm = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
MAP = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])

QUERIES = [('P01', 15 * 60 + 15, 15 * 60 + 35), ('P20', 24 * 60 + 10, 24 * 60 + 40)]

for ep, lo, hi in QUERIES:
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    print(f'\n=== {ep} [{lo // 60}m{lo % 60:02d}s – {hi // 60}m{hi % 60:02d}s]')
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        t = re.match(r'(\d+)m(\d+)s', e.get('timestamp') or '')
        if not t:
            continue
        sec = int(t.group(1)) * 60 + int(t.group(2))
        if lo <= sec <= hi:
            cand = [v for k, v in MAP.items()
                    if k.startswith(f'[{ep}]') and k.endswith('|' + e['timestamp'])]
            mapped = cand[0] if cand else '(无此 key)'
            exists = os.path.exists(os.path.join(B, 'docs', 'frames', mapped)) if cand else False
            print(f"   {e['timestamp']:>7s}  {e.get('text')[:30]:32s} -> {mapped} 存在={exists}")
