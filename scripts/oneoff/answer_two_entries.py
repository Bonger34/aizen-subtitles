# -*- coding: utf-8 -*-
"""回答"那 2 条到底找没找到": 
1) 全系列密集扫描是否覆盖了那两秒(区间内采样);
2) 该时间附近密集扫描都读到了什么;
3) 全系列候选里有没有出现目标文本(口 / 敬告)。
"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
EXT = os.path.join(B, 'review', 'ext_regions')
D2 = os.path.join(B, 'review', 'dense2')


def sec_of(t):
    m = re.match(r'(\d+)m(\d+)s', t)
    return int(m.group(1)) * 60 + int(m.group(2))


def covered(ep, sec):
    d = json.load(open(os.path.join(EXT, f'{ep}.json'), encoding='utf-8'))
    ivs = [(x[0], x[1]) for x in d['regions']['BAND'] + d['regions']['LOW']]
    return [(round(a, 1), round(b, 1)) for a, b in ivs if a - 0.5 <= sec <= b + 0.5]


for ep, ts in (('P22', '17m53s'), ('P24', '18m11s')):
    sec = sec_of(ts)
    print(f'=== {ep} {ts} (第 {sec} 秒)')
    print(f'   该秒被检测区间覆盖: {covered(ep, sec) or "★完全无区间★"}')
    d = json.load(open(os.path.join(D2, f'{ep}.json'), encoding='utf-8'))
    near = [c for c in d['cands'] if abs(c['sec'] - sec) <= 15]
    print(f'   该秒 ±15s 内密集扫描的候选 {len(near)} 条:')
    for c in sorted(near, key=lambda x: x['sec']):
        print(f"      {c['t']:>7s} [{c['text']}] bef={c['bef']}")
    print()

# 全系列候选里搜目标文本
print('=== 全系列密集扫描候选中检索目标文本')
hits = {'敬告': [], '口': []}
for f in sorted(os.listdir(D2)):
    if not f.endswith('.json'):
        continue
    d = json.load(open(os.path.join(D2, f), encoding='utf-8'))
    for c in d['cands']:
        t = re.sub(r'[^\u4e00-\u9fff]', '', c['text'])
        if '敬告' in t:
            hits['敬告'].append((d['ep'], c['t'], c['text']))
        if t == '口':
            hits['口'].append((d['ep'], c['t'], c['text']))
for k, v in hits.items():
    print(f'  「{k}」 命中 {len(v)}: {v[:5]}')
