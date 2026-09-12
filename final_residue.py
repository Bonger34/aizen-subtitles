# -*- coding: utf-8 -*-
"""最终残留分析: 从 415 条"疑似漏句"里排除片尾段与跨集重复(歌词碎片), 看正片还剩多少。"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
d = json.load(open(os.path.join(B, 'review', 'converge.json'), encoding='utf-8'))
rows = d['dialogue'] + [dict(c, sec=int(c['t'].split('m')[0]) * 60 + int(c['t'].split('m')[1].rstrip('s')))
                        for c in d['short']]
print('疑似漏句', len(d['dialogue']), '| 短文本', len(d['short']))


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


rep = collections.Counter(cn(r['text']) for r in rows)
main, tail, repd = [], 0, 0
for r in rows:
    t = cn(r['text'])
    if r['sec'] >= (21 * 60 if r['ep'] == 'P25' else 22 * 60 + 30):
        tail += 1
        continue
    if rep[t] >= 3:
        repd += 1
        continue
    main.append(r)
print(f'排除: 片尾/图鉴段 {tail}, 跨集重复(歌词碎片) {repd}')
print(f'正片残留 {len(main)} 条:')
for r in sorted(main, key=lambda x: (x['ep'], x['sec'])):
    print(f"   {r['ep']} {r['t']:>7s}  [{r['text']}]  全库最高分={r['best_all']} 邻域={r.get('near')}")
