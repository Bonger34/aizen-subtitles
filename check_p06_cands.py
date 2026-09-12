# -*- coding: utf-8 -*-
"""检查修好后的 P06 候选: 与全库双向匹配, 分出"库中已有"和"真缺"。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
d = json.load(open(os.path.join(B, 'review', 'dense2', 'P06.json'), encoding='utf-8'))


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def score(a, b):
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return min(sum(1 for ch in a if ch in sb) / len(a), sum(1 for ch in b if ch in sa) / len(b))


lib = []
for fn in sorted(os.listdir(CLEAN)):
    if fn.endswith('.json'):
        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
            t = cn(e.get('text'))
            if t:
                lib.append((fn[1:4], e['timestamp'], t))

covered, novel = [], []
for c in d['cands']:
    n = cn(c['text'])
    if len(n) < 2:
        continue
    best, arg = 0.0, None
    for ep, ts, lt in lib:
        if abs(len(lt) - len(n)) > 10:
            continue
        s = score(n, lt)
        if s > best:
            best, arg = s, (ep, ts, lt)
    (covered if best >= 0.7 else novel).append((c, best, arg))

print(f"P06 候选 {len(d['cands'])}: 库中已有 {len(covered)} / 真缺(全库都无) {len(novel)}")
print('\n真缺(按时间):')
for c, best, arg in sorted(novel, key=lambda x: x[0]['sec']):
    print(f"   {c['t']:>7s}  [{c['text']}]   最近库={arg}({best:.2f})")
