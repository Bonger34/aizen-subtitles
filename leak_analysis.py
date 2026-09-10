# -*- coding: utf-8 -*-
"""leak_analysis.py — 量化剩余漏句风险: 库中短条目、采样密度、单字台词"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(BASE, 'subtitle_clean')
REVIEW = os.path.join(BASE, 'review')

# 1. 库中短条目统计
stats = {1: 0, 2: 0, 3: 0, 4: 0}
tot = 0
for f in os.listdir(CLEAN):
    if not f.endswith('.json'):
        continue
    for e in json.load(open(os.path.join(CLEAN, f), encoding='utf-8')):
        n = len(re.sub(r'[^\u4e00-\u9fff]', '', e['text']))
        tot += 1
        if n in stats:
            stats[n] += 1
print(f'库总 {tot}: 单字 {stats[1]}, 双字 {stats[2]}, 三字 {stats[3]}, 四字 {stats[4]}')

# 2. 各集采样密度(密集扫描)
print('\n集  区间  采样  序列  采样/区间  序列/区间')
for ep in [f'P{i:02d}' for i in range(1, 26)]:
    p = os.path.join(REVIEW, f'dense_cont_{ep}.json')
    if not os.path.exists(p):
        continue
    d = json.load(open(p, encoding='utf-8'))
    iv, sa, sq = d['intervals'], d['samples'], len(d['seqs'])
    if ep in ('P01', 'P06', 'P13', 'P19', 'P25'):
        print(f'{ep}  {iv:5d} {sa:5d} {sq:5d}   {sa/iv:6.1f}   {sq/iv:6.1f}')

# 3. 单字台词: 检查密集扫描候选里被过滤的(用 raw 字段)
#    scan_cont.py 已丢弃 <2 字的, 故只能看現有 seqs 中 2 字占比
two_ratio = []
for ep in [f'P{i:02d}' for i in range(1, 26)]:
    p = os.path.join(REVIEW, f'dense_cont_{ep}.json')
    if not os.path.exists(p):
        continue
    d = json.load(open(p, encoding='utf-8'))
    if not d['seqs']:
        continue
    n2 = sum(1 for s in d['seqs'] if len(re.sub(r'[^\u4e00-\u9fff]', '', s['text'])) == 2)
    two_ratio.append(n2 / len(d['seqs']))
print(f'\n各集 2 字序列占比均值: {sum(two_ratio)/len(two_ratio):.1%}(样本 {len(two_ratio)} 集)')
