# -*- coding: utf-8 -*-
"""把"仅LOW 区间"OCR 出的候选分类: 版权声明卡 / 片尾歌词 / 噪声 / 疑似台词。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
p = os.path.join(B, 'review', 'ext_cands.json')
d = json.load(open(p, encoding='utf-8'))
print('已处理集数:', len(d), sorted(d))

COPY = re.compile(r'版权|新创华|文化发展|中国大陆|上海新')
LYRIC = ('就算遇到挫折也决不望而却步', '因为你我的牵绊永不间断', '不经意地翻开相册',
         '永不间断', '望而却步', '牵绊')
tally, talk = {}, []
for ep, v in sorted(d.items()):
    for c in v['cands']:
        t = c['text']
        if COPY.search(t):
            k = '版权声明卡'
        elif any(x in t for x in LYRIC):
            k = '片尾歌词'
        elif len(re.sub(r'[^\u4e00-\u9fff]', '', t)) < 4:
            k = '噪声(数字/单字)'
        else:
            k = '疑似台词'
            talk.append((ep, c['t'], t, c['bef']))
        tally[k] = tally.get(k, 0) + 1
for k, v in sorted(tally.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}')
print('\n疑似台词明细:')
for ep, t, tx, b in talk:
    print(f'  {ep} {t:>7s} [{tx}] (bef={b})')
