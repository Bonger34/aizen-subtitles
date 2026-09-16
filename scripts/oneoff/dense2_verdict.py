# -*- coding: utf-8 -*-
"""判定"像中文台词"的候选类是真漏句还是同句异读:
   * 该位置 ±5s 内库中**有条目** -> 很可能是同一句的差异读取(需人工看画面确认)
   * 该位置 ±5s 内库中**无条目** -> 高度疑似真漏句
"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
rows = json.load(open(os.path.join(B, 'review', 'dense2_clusters.json'), encoding='utf-8'))
CHOSEN = os.path.join(B, 'review', 'dense2_dialogue_all.txt')

# 复用上一步筛出的"像中文台词"集合
txt = open(CHOSEN, encoding='utf-8').read()
reps = set(re.findall(r'^  \[(.+?)\] ×', txt, re.M))
picked = [r for r in rows if r['rep'] in reps]
print('像中文台词的类', len(picked))


def sec_of(t):
    m = re.match(r'(\d+)m(\d+)s', t)
    return int(m.group(1)) * 60 + int(m.group(2))


lib = {}
for fn in os.listdir(CLEAN):
    if fn.endswith('.json'):
        ep = fn[1:4]
        lib[ep] = [(sec_of(e['timestamp']), e['timestamp'], e.get('text') or '')
                   for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))]

真漏, 同位置有 = [], []
for r in picked:
    hits = []
    for i in r['items']:
        s = sec_of(i['t'])
        near = [x for x in lib.get(i['ep'], []) if abs(x[0] - s) <= 5]
        hits.append((i['ep'], i['t'], [(x[1], x[2]) for x in near]))
    if all(len(h[2]) == 0 for h in hits):
        真漏.append((r, hits))
    else:
        同位置有.append((r, hits))

print(f'  该位置 ±5s 内库中无条目(高度疑似真漏): {len(真漏)} 类')
print(f'  该位置有库条目(疑似同句异读): {len(同位置有)} 类')
lines = ['候选类判定:', f'  疑似真漏 {len(真漏)} 类 / 同句异读 {len(同位置有)} 类', '',
         '=== 高度疑似真漏(位置附近库里完全没有条目) ===']
for r, hits in 真漏:
    lines.append(f"  [{r['rep']}]  " + ' '.join(f"{h[0]}{h[1]}" for h in hits[:4]))
lines.append('')
lines.append('=== 疑似同句异读(位置附近有条目, 列出对照) ===')
for r, hits in 同位置有:
    ex = next((h for h in hits if h[2]), None)
    lines.append(f"  [{r['rep']}]  @{ex[0]}{ex[1]}  库内={[x[1] for x in ex[2]][:2]}")
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'dense2_verdict.txt'), 'w', encoding='utf-8').write(txt)
print(txt[:5000])
