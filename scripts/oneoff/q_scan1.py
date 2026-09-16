# -*- coding: utf-8 -*-
"""q_scan1.py — 文本质量侦察: 统计库中可疑条目(短文本/含非中文字符/重复), 输出清单。
用法: python q_scan1.py
输出: review/q_scan1.txt
"""
import json
import os
import re
from collections import Counter

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
CJK = re.compile(r'[\u4e00-\u9fff]')
NOISE = re.compile(r'[0-9A-Za-z]')

rows = []
for fn in sorted(os.listdir(CLEAN)):
    if not fn.endswith('.json'):
        continue
    title = fn[:-5]
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        rows.append((title, e.get('timestamp', ''), e.get('text', ''), e.get('similarity')))

L = [len(r[2]) for r in rows]
dist = Counter(L)
short = [r for r in rows if len(r[2]) <= 3]
withnum = [r for r in rows if NOISE.search(r[2])]
nocjk = [r for r in rows if not CJK.search(r[2])]
txt_dup = Counter(r[2] for r in rows)
dups = [(t, c) for t, c in txt_dup.items() if c > 1]

lines = [f'总条目 {len(rows)}', f'长度分布(长度:条数) {sorted(dist.items())}',
         f'长度<=3 的 {len(short)} 条', f'含数字/拉丁字母的 {len(withnum)} 条',
         f'不含汉字的 {len(nocjk)} 条', f'全库重复文本 {len(dups)} 种', '', '=== 长度<=3 ===']
for t, ts, x, s in short:
    lines.append(f'  {t} {ts:>7s} [{x}]  sim={s}')
lines.append('')
lines.append('=== 含数字/拉丁字母 ===')
for t, ts, x, s in withnum[:200]:
    lines.append(f'  {t} {ts:>7s} [{x}]  sim={s}')
lines.append('')
lines.append('=== 不含汉字 ===')
for t, ts, x, s in nocjk[:80]:
    lines.append(f'  {t} {ts:>7s} [{x}]  sim={s}')
lines.append('')
lines.append('=== 全库重复文本(>=3 次) ===')
for t, c in sorted(dups, key=lambda z: -z[1])[:80]:
    if c >= 3:
        lines.append(f'  {c:3d}x  [{t}]')

out = '\n'.join(lines)
os.makedirs(os.path.join(B, 'review'), exist_ok=True)
open(os.path.join(B, 'review', 'q_scan1.txt'), 'w', encoding='utf-8').write(out)
print(out[:6000])
