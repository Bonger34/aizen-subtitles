# -*- coding: utf-8 -*-
"""删除"与已映射帧字节完全相同"的重复孤儿帧。

安全保证: 仅当该孤儿帧的 MD5 能在【已被 frames_map 引用的帧】中找到完全相同的一份
且该引用帧确实存在于磁盘时, 才允许删除 —— 即画面内容 100% 另有留存。

用法:
  python orphan_del.py          # 只列出, 不删
  python orphan_del.py --apply  # 实际删除
"""
import hashlib
import json
import os
import sys

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'docs', 'frames')
fm = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
MAP = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])
REF = {v for v in MAP.values() if isinstance(v, str)}


def md5(p):
    with open(p, 'rb') as fh:
        return hashlib.md5(fh.read()).hexdigest()


ref_hash = {}
for f in sorted(REF):
    p = os.path.join(FR, f)
    if os.path.exists(p):
        ref_hash.setdefault(md5(p), []).append(f)

files = sorted(os.listdir(FR))
orphans = [f for f in files if f not in REF]
dup, uniq = [], []
for f in orphans:
    d = md5(os.path.join(FR, f))
    (dup if d in ref_hash else uniq).append((f, ref_hash.get(d, [''])[0]))

lines = [f'孤儿 {len(orphans)} / 可删(与已引用帧字节相同) {len(dup)} / 保留(独有内容) {len(uniq)}', '']
lines += [f'{f}\t== {g}' for f, g in dup]
open(os.path.join(B, 'review', 'orphan_dup_deleted.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
print(lines[0])

if '--apply' in sys.argv:
    freed = 0
    for f, g in dup:
        p = os.path.join(FR, f)
        freed += os.path.getsize(p)
        os.remove(p)
    print(f'已删除 {len(dup)} 个文件, 释放 {freed / 1048576:.1f} MB')
else:
    print('(未加 --apply, 仅列出清单 -> review/orphan_dup_deleted.txt)')
