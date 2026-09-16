# -*- coding: utf-8 -*-
"""
verify_consistency.py — 最终一致性校验
1. 每条库条目是否有 frames_map 键
2. 该键指向的帧文件是否存在
3. frames_map 键是否都能在库中找到对应条目(孤儿键)
4. 统计无帧条目清单
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(BASE, 'subtitle_clean')
FRAMES = os.path.join(BASE, 'docs', 'frames')
FMAP = os.path.join(BASE, 'docs', 'frames_map.js')

src = open(FMAP, encoding='utf-8').read()
m = re.search(r'=\s*(\{.*?\})\s*;', src, re.S)
FMAP = json.loads(m.group(1))
print('frames_map 键数', len(FMAP))

miss_key = []
miss_file = []
lib_total = 0
lib_keys = set()
for f in sorted(os.listdir(CLEAN)):
    if not f.endswith('.json'):
        continue
    title = f[:-5]
    arr = json.load(open(os.path.join(CLEAN, f), encoding='utf-8'))
    lib_total += len(arr)
    for e in arr:
        key = f'{title}|{e["timestamp"]}'
        lib_keys.add(key)
        if key not in FMAP:
            miss_key.append(key)
        else:
            fp = os.path.join(FRAMES, FMAP[key])
            if not os.path.exists(fp):
                miss_file.append((key, FMAP[key]))

orphan = [k for k in FMAP if k not in lib_keys]
print(f'库条目 {lib_total}')
print(f'缺 frames_map 键: {len(miss_key)}')
for k in miss_key[:20]:
    print('  ', k)
print(f'键存在但帧文件缺失: {len(miss_file)}')
for k, v in miss_file[:20]:
    print('  ', k, '->', v)
print(f'孤儿键(无库条目): {len(orphan)}')
for k in orphan[:20]:
    print('  ', k)
