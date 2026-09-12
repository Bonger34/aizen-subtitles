# -*- coding: utf-8 -*-
"""查看密集扫描的候选, 判断哪些是真漏句、哪些是匹配判据造成的误报。"""
import json
import os
import re
import sys

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
ep = sys.argv[1] if len(sys.argv) > 1 else 'P01'
d = json.load(open(os.path.join(B, 'review', 'dense2', f'{ep}.json'), encoding='utf-8'))
fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
lib = [(int(e['timestamp'].split('m')[0]) * 60 + int(e['timestamp'].split('m')[1].rstrip('s')),
        e.get('text') or '') for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))]
print(f"{ep}: 候选 {len(d['cands'])} 条")


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


real, dup = [], []
for c in d['cands']:
    t = cn(c['text'])
    win = [(lt, lx) for lt, lx in lib if abs(lt - c['sec']) <= 5]
    back = max((sum(1 for ch in cn(lx) if ch in t) / len(cn(lx)) for _, lx in win), default=0.0)
    (dup if back >= 0.6 else real).append((c, round(back, 2), win[:2]))
print(f'  双向匹配后: 库里已有(判据误报) {len(dup)}, 真候选 {len(real)}')
print('\n真候选:')
for c, back, win in real[:60]:
    print(f"   {c['t']:>7s} [{c['text']}]  反向包含度={back} 库近邻={[x for _, x in win]}")
print('\n判据误报样例:')
for c, back, win in dup[:15]:
    print(f"   {c['t']:>7s} [{c['text']}]  反向包含度={back} 库近邻={[x for _, x in win]}")
