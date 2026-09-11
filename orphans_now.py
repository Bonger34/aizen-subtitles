# -*- coding: utf-8 -*-
"""列出当前孤儿帧(未被 frames_map 引用的文件), 与之前的 102 张对比, 找出新增的。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'Web', 'frames')
MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                           open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read(),
                           re.S).group(1))
ref = {v for v in MAP.values() if isinstance(v, str)}
files = set(os.listdir(FR))
orphans = sorted(files - ref)
print(f'帧文件 {len(files)} / 被引用 {len(ref)} / 孤儿 {len(orphans)}')

prev = set()
p = os.path.join(B, 'review', 'orphan_final.txt')
if os.path.exists(p):
    prev = set(re.findall(r'^  (P\d+_\S+\.jpg)', open(p, encoding='utf-8').read(), re.M))
new = [f for f in orphans if f not in prev]
gone = sorted(prev - files)
print(f'此前记录的 102 张中: 已不存在 {len(gone)}, 仍存在 {len(prev & files)}')
print(f'新增孤儿 {len(new)}:')
for f in new:
    print('   ', f, os.path.getsize(os.path.join(FR, f)) // 1024, 'KB')
json.dump({'orphans': orphans, 'new': new},
          open(os.path.join(B, 'review', 'orphans_now.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
