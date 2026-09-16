# -*- coding: utf-8 -*-
"""dup_check.py — 找出库内同集同时间戳的重复条目"""
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根(scripts/pipeline 的上三级)
CLEAN = os.path.join(_ROOT, "subtitle_clean")
total = 0
dups = []
for fn in sorted(os.listdir(CLEAN)):
    if not fn.endswith('.json'):
        continue
    arr = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
    total += len(arr)
    c = Counter(e['timestamp'] for e in arr)
    for ts, n in c.items():
        if n > 1:
            texts = [e['text'] for e in arr if e['timestamp'] == ts]
            dups.append((fn[:4], ts, n, texts))
print('库总条数', total)
print('同秒重复组数', len(dups))
for ep, ts, n, texts in dups:
    print(' ', ep, ts, n, texts)
