# -*- coding: utf-8 -*-
"""q_stat2.py — 统计 unmatched 条目里"时间线另有读数"的部分, 按相似度分档, 便于人工核对。

unmatched 的阈值是 sim<0.55, 但真实错字修正的相似度天然偏低(如 整坐城币得救 ->
整座城市得救了 只有 0.5), 所以这一档里藏着真修正, 需要单独捞出来看。
用法: python q_stat2.py [--lo 0.35] [--hi 0.55] [--show N]
"""
import json
import os
import sys
from collections import Counter

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = json.load(open(os.path.join(B, 'review', 'q_align_tl.json'), encoding='utf-8'))
lo = float(sys.argv[sys.argv.index('--lo') + 1]) if '--lo' in sys.argv else 0.35
hi = float(sys.argv[sys.argv.index('--hi') + 1]) if '--hi' in sys.argv else 0.55
show = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 40

buckets = Counter()
rows = []
for ep in sorted(d):
    for r in d[ep]['items']:
        if r['verdict'] != 'unmatched':
            continue
        s = r.get('best_sim')
        if s is None:
            buckets['无任何匹配'] += 1
            continue
        if s < 0.20:
            buckets['<0.20'] += 1
        elif s < lo:
            buckets[f'{0.20:.2f}~{lo:.2f}'] += 1
        elif s < hi:
            buckets[f'{lo:.2f}~{hi:.2f}'] += 1
            rows.append((ep, r))
        else:
            buckets[f'{hi:.2f}~1.00'] += 1
print('unmatched 分布:', dict(buckets))
print(f'\n=== sim {lo}~{hi} 档 {len(rows)} 条, 显示前 {show} ===')
for ep, r in rows[:show]:
    print(f"  {ep} {r['ts']:>7s} sim={r['best_sim']:.2f} sup={r.get('support')} dt={r.get('dt'):+.2f}s")
    print(f"      旧[{r['old']}]")
    print(f"      读[{r.get('new')}]")
