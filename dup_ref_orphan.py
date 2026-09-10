# -*- coding: utf-8 -*-
"""交叉检查: 被两个 key 共用的帧(119 处) 附近是否有孤儿帧可作为其中一个条目的正确配图。"""
import json
import os
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
fm = open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read()
m = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])
scan = {r['f']: r for r in json.load(open(os.path.join(B, 'review', 'orphan_scan.json'), encoding='utf-8'))['recs']}

rev = collections.defaultdict(list)
for k, v in m.items():
    rev[v].append(k)
dup = {f: sorted(ks, key=lambda k: k.split('|')[1]) for f, ks in rev.items() if len(ks) > 1}

lines = [f'共用同一帧的条目组: {len(dup)}']
with_orphan = 0
for f, ks in sorted(dup.items()):
    ep = f[:3]
    # 该组各条目秒数
    secs = []
    for k in ks:
        t = k.split('|')[1]
        mm = t.replace('m', ' ').replace('s', '').split()
        secs.append(int(mm[0]) * 60 + int(mm[1]))
    lo, hi = min(secs), max(secs)
    cand = [g for g in scan if g.startswith(ep + '_') and scan[g]['ep'] is not None
            and lo - 2 <= scan[g]['sec'] <= hi + 2 and not scan[g]['same'] and not scan[g]['near']]
    if cand:
        with_orphan += 1
        lines.append(f'  {f} 条目秒={secs} 候选孤儿={cand}')
lines.insert(1, f'其中附近存在 A 组孤儿帧的: {with_orphan}')
open(os.path.join(B, 'review', 'dup_ref_orphan.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:15]))
