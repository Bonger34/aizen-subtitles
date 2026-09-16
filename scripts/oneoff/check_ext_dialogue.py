# -*- coding: utf-8 -*-
"""核查带外候选里"像对白"的几条: 看库中该时段有什么, 以及这些句子是否已存在于全库。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')

lib = {}
for fn in os.listdir(CLEAN):
    m = re.match(r'\[(P\d+)\]', fn)
    if m:
        lib[m.group(1)] = [(e['timestamp'], e.get('text') or '')
                           for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))]
allrows = [(ep, ts, tx) for ep, rows in lib.items() for ts, tx in rows]


def sec(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2))


CTX = [('P18', 8 * 60 + 15, 8 * 60 + 28), ('P18', 9 * 60 + 26, 9 * 60 + 36),
       ('P11', 10 * 60 + 6, 10 * 60 + 16)]
for ep, lo, hi in CTX:
    print(f'--- {ep} {lo // 60}m{lo % 60:02d}s ~ {hi // 60}m{hi % 60:02d}s 库内条目:')
    hits = [(ts, tx) for ts, tx in lib[ep] if lo <= sec(ts) <= hi]
    for ts, tx in hits:
        print(f'      {ts:>7s}  {tx}')
    if not hits:
        print('      (该时段库中无条目!)')

print('\n这些句子是否已存在于全库(去标点子串匹配):')
for q in ['没关系的', '明天我仍然会继续', '制作恤', '奥特战士的爸爸哦',
          '打败怪兽时的必杀技超帅', '整个世界都在等着我', '全世界都在等着我', '给你']:
    key = re.sub(r'[^\u4e00-\u9fff]', '', q)
    hits = [(ep, ts, tx) for ep, ts, tx in allrows if key in re.sub(r'[^\u4e00-\u9fff]', '', tx)]
    print(f'  [{"有" if hits else "无"}] 「{q}」 {len(hits)} 处')
    for ep, ts, tx in hits[:3]:
        print(f'        {ep} {ts} {tx[:40]}')
