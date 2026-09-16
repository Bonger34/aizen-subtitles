# -*- coding: utf-8 -*-
"""梳理"多条条目共用同一张配图"的情况: 数量、间隔、文本是否相同、错在哪一条。

输出 review/shared_frames.txt
"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                           open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read(),
                           re.S).group(1))

text_of = {}
for fn in os.listdir(CLEAN):
    if not fn.endswith('.json'):
        continue
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        text_of[f"{fn[:-5]}|{e['timestamp']}"] = e.get('text') or ''


def sec(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2))


rev = collections.defaultdict(list)
for k, v in MAP.items():
    rev[v].append(k)
groups = {f: ks for f, ks in rev.items() if len(ks) > 1}

sizes = collections.Counter(len(ks) for ks in groups.values())
spread = collections.Counter()
same_text = diff_text = 0
detail = []
for f, ks in sorted(groups.items()):
    ks = sorted(ks, key=lambda k: sec(k.split('|')[1]))
    secs = [sec(k.split('|')[1]) for k in ks]
    spread[max(secs) - min(secs)] += 1
    ts = [text_of.get(k, '') for k in ks]
    if len(set(ts)) == 1:
        same_text += 1
    else:
        diff_text += 1
    detail.append((f, [(k.split('|')[1], t) for k, t in zip(ks, ts)]))

# 每个被共用帧的名字与它自身时间戳的关系
name_matches = collections.Counter()
for f, ks in groups.items():
    m = re.match(r'(P\d+)_(\d+)m(\d+)s\.jpg', f)
    if not m:
        name_matches['帧名不合法'] += 1
        continue
    nsec = int(m.group(2)) * 60 + int(m.group(3))
    secs = [sec(k.split('|')[1]) for k in ks]
    name_matches['帧名与其中一条时间戳相同'] += (nsec in secs)
    name_matches['帧名与两条都不同'] += (nsec not in secs)

lines = [f'共用配图的帧: {len(groups)} 个(占 {len(rev)} 个被引用帧的 {len(groups) / len(rev) * 100:.1f}%)',
         f'  每条被几条条目引用: {dict(sizes)}',
         f'  组内时间戳跨度分布: {dict(sorted(spread.items()))}',
         f'  两条文本相同(无害): {same_text} / 文本不同(其中一条配图必错): {diff_text}',
         f'  帧名归属: {dict(name_matches)}', '']
for f, rows in detail:
    lines.append(f'  {f}')
    for t, tx in rows:
        lines.append(f'      {t:>7s}  {tx}')
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'shared_frames.txt'), 'w', encoding='utf-8').write(txt)
print('\n'.join(lines[:200]))
