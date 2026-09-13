# -*- coding: utf-8 -*-
"""q_stat.py — 统计 q_align_tl.json 各判定/编辑类型的分布, 并抽样打印。"""
import json
import os
import sys
from collections import Counter

B = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(B, 'review', 'q_align_tl.json'), encoding='utf-8'))
verdicts, kinds = Counter(), Counter()
per_ep = Counter()
rows = []
for ep in sorted(d):
    for r in d[ep]['items']:
        verdicts[r['verdict']] += 1
        if r['verdict'] == 'review':
            kinds[r.get('kind', '?')] += 1
            per_ep[ep] += 1
            rows.append((ep, r))
print('判定分布:', dict(verdicts))
print('review 的编辑类型:', dict(kinds))
print('review 按集:', dict(sorted(per_ep.items())))
want = sys.argv[1] if len(sys.argv) > 1 else 'replace'
n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
sel = [x for x in rows if x[1].get('kind') == want]
print(f'\n=== review/{want} 抽样 {min(n, len(sel))}/{len(sel)} ===')
for ep, r in sel[:n]:
    print(f"  {ep} {r['ts']:>7s} sim={r['best_sim']:.2f} sup={r.get('support')} "
          f"dt={r.get('dt'):+.2f}s {r.get('desc', '')[:60]}")
    print(f"      旧[{r['old']}]")
    print(f"      新[{r['new']}]")
