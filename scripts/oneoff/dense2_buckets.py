# -*- coding: utf-8 -*-
"""把 461 类疑似台词按"与库最近条目的双向分"分档, 分档给出样例与计数。"""
import json
import os
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
rows = json.load(open(os.path.join(B, 'review', 'dense2_clusters.json'), encoding='utf-8'))
print('类数', len(rows), '原始条数', sum(r['n'] for r in rows))
buckets = collections.defaultdict(list)
for r in rows:
    s = r['best_score']
    k = ('A 与库高度相近(>=0.6, 多为同句差异读取)' if s >= 0.6 else
         'B 中等相近(0.4~0.6)' if s >= 0.4 else
         'C 低相近(0.2~0.4)' if s >= 0.2 else 'D 几乎无相近(<0.2)')
    buckets[k].append(r)
for k in sorted(buckets):
    print(f'{k}: {len(buckets[k])} 类')

lines = []
for k in sorted(buckets):
    lines.append(f'=== {k}: {len(buckets[k])} 类')
    for r in sorted(buckets[k], key=lambda x: -x['n'])[:60]:
        items = r['items'][:4]
        loc = ' '.join(f"{i['ep']}{i['t']}" for i in items)
        lines.append(f"   [{r['rep']}] ×{r['n']}  {loc}   最近库={r['best_lib']}({r['best_score']})")
    lines.append('')
open(os.path.join(B, 'review', 'dense2_buckets.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
print('写出 review/dense2_buckets.txt')
