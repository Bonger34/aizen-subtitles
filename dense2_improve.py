# -*- coding: utf-8 -*-
"""统计: 密集扫描候选里有多少是"库文本是画面文本的真子集且缺的是数字"这类可无损改进项。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
rows = json.load(open(os.path.join(B, 'review', 'dense2_clusters.json'), encoding='utf-8'))


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


improve, other = [], []
for r in rows:
    rep = r['rep']
    lib = r['best_lib']
    if not lib:
        other.append(r)
        continue
    lt = cn(lib[2])
    if lt and lt in rep and rep != lt:
        extra = rep.replace(lt, '')
        if all(c.isdigit() for c in extra):
            improve.append((r, lt, extra))
            continue
    other.append(r)

print(f'可无损改进(库文本是画面文本的子串, 缺的只是数字): {len(improve)} 类')
for r, lt, extra in improve[:40]:
    loc = ' '.join(f"{i['ep']}{i['t']}" for i in r['items'][:3])
    print(f"   [{lt}] -> [{r['rep']}]  补的数字={extra}  {loc}")
print(f'\n其余 {len(other)} 类不是这类')
lines = [f'可无损改进项 {len(improve)} 类(库文本 + 缺失数字 = 画面文本):', '']
lines += [f"  {lt}  ->  {r['rep']}   (补 {extra})  {' '.join(i['ep'] + i['t'] for i in r['items'][:3])}"
          for r, lt, extra in improve]
open(os.path.join(B, 'review', 'dense2_improve.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
