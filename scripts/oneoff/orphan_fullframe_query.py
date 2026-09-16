# -*- coding: utf-8 -*-
"""在字幕库中检索整帧 OCR 新发现的中文句子, 判断是否已被收录。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')

QUERIES = ['不管前方有什么艰难险阻', '不管前方有多么昏暗阴沉', '全世界都在等着我',
           '它的特征是身上有条纹花纹', '它的武器是从鼻尖的角中', '身高78米', '体重21万7千吨',
           '仿若能天长地久', '就算遇到挫折也决不望而却步', '你是怎么想的',
           '因为有想要守护的东西', '之前那里有颗行星也爆炸了', '找一下想去避难的人',
           '不管明天世界会变成什么样子', '这一瞬间是亲情', '变得更加强大', '开工干活吧',
           '那我也走了', '好咧', '身高', '体重']

rows = []
for fn in sorted(os.listdir(CLEAN)):
    m = re.match(r'\[(P\d+)\]', fn)
    if not m:
        continue
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        rows.append((m.group(1), e['timestamp'], e.get('text') or ''))

lines = ['整帧 OCR 新发现中文句 / 库中检索结果(去标点后子串匹配):', '']
for q in QUERIES:
    key = re.sub(r'[^\u4e00-\u9fff]', '', q)
    hits = [(ep, ts, tx) for ep, ts, tx in rows
            if key and key in re.sub(r'[^\u4e00-\u9fff]', '', tx)]
    mark = '库中有' if hits else '★库中无★'
    lines.append(f'  [{mark}] 「{q}」 命中 {len(hits)}')
    for ep, ts, tx in hits[:3]:
        lines.append(f'        {ep} {ts}  {tx[:40]}')
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'orphan_fullframe_query.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
