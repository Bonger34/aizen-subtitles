# -*- coding: utf-8 -*-
"""一次性统计脚本：各集提升候选分布（互含残句/近重复/超短）"""
import json, os, re
from collections import defaultdict

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\subtitle_clean'

def sec(s):
    m = re.match(r'(\d+)m(\d+)s', s)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else 0

def lcs(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i][j - 1], dp[i - 1][j])
    return dp[m][n]

stats = defaultdict(lambda: {'tot': 0, 'contain': 0, 'dup': 0, 'short': 0})
for fn in os.listdir(BASE):
    m = re.match(r'^\[(P\d{2})\]', fn)
    if not m or not fn.endswith('.json'):
        continue
    ep = m.group(1)
    data = json.load(open(os.path.join(BASE, fn), encoding='utf-8'))
    data.sort(key=lambda r: sec(r.get('timestamp', '')))
    st = stats[ep]
    st['tot'] = len(data)
    for i, r in enumerate(data):
        t = r.get('text', '').strip()
        s = sec(r.get('timestamp', ''))
        if len(t) <= 2:
            st['short'] += 1
        for j in (i - 1, i + 1):
            if j < 0 or j >= len(data):
                continue
            o = data[j]
            to = o.get('text', '').strip()
            if to == t:
                continue
            if abs(sec(o.get('timestamp', '')) - s) > 3:
                continue
            if t and to and len(t) >= 2 and len(to) >= 2 and (t in to or to in t):
                st['contain'] += 1
            elif len(t) >= 4 and len(to) >= 4 and lcs(t, to) / min(len(t), len(to)) >= 0.85:
                st['dup'] += 1

cand = {}
print('%-6s%6s%6s%6s%6s%8s' % ('集', '总数', '互含', '近重复', '超短', '候选合计'))
for ep in sorted(stats):
    s = stats[ep]
    c = s['contain'] + s['dup'] + s['short']
    cand[ep] = c
    print('%-6s%6d%6d%6d%6d%8d' % (ep, s['tot'], s['contain'], s['dup'], s['short'], c))
best = sorted(cand, key=lambda e: -cand[e])[:3]
print('候选最多:', [(e, cand[e]) for e in best])
