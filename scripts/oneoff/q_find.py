# -*- coding: utf-8 -*-
"""q_find.py — 在库中按文本片段查找条目(集/时间戳/文本), 并标出该条目在两种判定中的状态。
用法: python q_find.py 整坐城币 好烫店
"""
import json
import os
import sys

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLEAN = os.path.join(B, 'subtitle_clean')
REVIEW = os.path.join(B, 'review')

j = {}
p = os.path.join(REVIEW, 'q_align_tl.json')
if os.path.exists(p):
    j = json.load(open(p, encoding='utf-8'))
verdict = {}
for ep, d in j.items():
    for r in d['items']:
        verdict[(ep, r['ts'])] = (r['verdict'], r.get('best_sim'), r.get('new'))

for kw in sys.argv[1:]:
    print(f'=== 搜索 [{kw}]')
    for fn in sorted(os.listdir(CLEAN)):
        if not fn.endswith('.json'):
            continue
        ep = fn.split(']')[0].lstrip('[')
        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
            if kw in e.get('text', ''):
                v = verdict.get((ep, e['timestamp']), ('-', None, None))
                print(f"  {ep} {e['timestamp']:>7s} [{e['text']}] 判定={v[0]} sim={v[1]}")
                if v[2]:
                    print(f"          时间线读到 [{v[2]}]")
