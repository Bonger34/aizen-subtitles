# -*- coding: utf-8 -*-
"""按文件内容哈希统计: 孤儿帧中有多少与已被 map 引用的帧字节完全相同(纯重复)。"""
import hashlib
import json
import os
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'Web', 'frames')
fm = open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read()
m = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])
ref = {v for v in m.values() if isinstance(v, str)}

files = sorted(os.listdir(FR))
orphans = [f for f in files if f not in ref]
print(f'磁盘 {len(files)} / 被引用 {len(ref)} / 孤儿 {len(orphans)}')


def h(p):
    with open(p, 'rb') as fh:
        return hashlib.md5(fh.read()).hexdigest()


refh = collections.defaultdict(list)
for f in sorted(ref):
    p = os.path.join(FR, f)
    if os.path.exists(p):
        refh[h(p)].append(f)

dup, uniq = [], []
for f in orphans:
    d = h(os.path.join(FR, f))
    (dup if d in refh else uniq).append((f, refh.get(d, [None])[0]))

lines = [f'孤儿 {len(orphans)}:与已引用帧字节相同 {len(dup)} / 独有内容 {len(uniq)}']
lines.append('\n独有内容的孤儿帧(需关注):')
for f, _ in uniq:
    lines.append(f'  {f}')
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'orphan_hash.txt'), 'w', encoding='utf-8').write(txt)
print(txt[:3000])
