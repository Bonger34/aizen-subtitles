# -*- coding: utf-8 -*-
"""检查 frames_map 中多个 key 指向同一帧的情况(可能与孤儿帧互为因果)。"""
import json
import os
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
fm = open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read()
m = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])

rev = collections.defaultdict(list)
for k, v in m.items():
    rev[v].append(k)

dup = {f: ks for f, ks in rev.items() if len(ks) > 1}
lines = [f'映射条目 {len(m)} / 唯一文件 {len(rev)} / 被多 key 引用的文件 {len(dup)}']
for f, ks in sorted(dup.items())[:40]:
    lines.append(f'  {f:18s} <- {ks}')
# 前缀是否一致(同集同名秒)
same_sec = sum(1 for f, ks in dup.items() if len({k[-7:] for k in ks}) == 1)
lines.append(f'其中所有 key 秒数完全相同的: {same_sec}')
open(os.path.join(B, 'review', 'map_dup_ref.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:10]))
