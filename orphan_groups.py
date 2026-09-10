# -*- coding: utf-8 -*-
"""孤儿帧分组 × 时间区域 交叉统计, 输出可读报告(A 组正片逐条列出)。"""
import json
import os
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
recs = json.load(open(os.path.join(B, 'review', 'orphan_scan.json'), encoding='utf-8'))['recs']

grp = lambda r: 'C' if r['same'] else ('B' if r['near'] else 'A')
cnt = collections.Counter()
for r in recs:
    tail = r['sec'] is not None and r['sec'] >= 22 * 60
    cnt[(grp(r), '片尾≥22m' if tail else '正片<22m')] += 1

lines = ['孤儿帧分组 × 时间区域']
for k in sorted(cnt):
    lines.append(f'  {k[0]}组 {k[1]}: {cnt[k]}')

A = sorted([r for r in recs if grp(r) == 'A' and r['sec'] is not None and r['sec'] < 22 * 60],
           key=lambda x: (x['ep'], x['sec']))
lines.append(f'\nA 组且位于正片(<22m) 共 {len(A)} 条:')
for r in A:
    lines.append(f"  {r['f']:16s} wr={r['wr']:.3f}")

Bo = sorted([r for r in recs if grp(r) == 'B' and r['sec'] is not None and r['sec'] < 22 * 60],
            key=lambda x: (x['ep'], x['sec']))
lines.append(f'\nB 组且位于正片(<22m) 共 {len(Bo)} 条(仅列前 40):')
for r in Bo[:40]:
    lines.append(f"  {r['f']:16s} wr={r['wr']:.3f} near={r['near'][:1]}")

open(os.path.join(B, 'review', 'orphan_groups.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:8]))
