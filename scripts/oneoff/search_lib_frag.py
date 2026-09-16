# -*- coding: utf-8 -*-
"""在库中检索候选文本的关键片段, 判断是"真缺"还是"同句变体"。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
QUERIES = ['场合', '沐浴', '面带微笑', '静静地听', '英勇奋战', '赞颂', '一口气毁灭',
           '流流汗', '时间地点']

rows = []
for fn in sorted(os.listdir(CLEAN)):
    if fn.endswith('.json'):
        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
            rows.append((fn[1:4], e['timestamp'], e.get('text') or ''))
for q in QUERIES:
    hits = [(ep, ts, tx) for ep, ts, tx in rows if q in tx]
    print(f'[{"有" if hits else "★无★"}] 「{q}」 {len(hits)}')
    for ep, ts, tx in hits[:5]:
        print(f'      {ep} {ts}  {tx}')
