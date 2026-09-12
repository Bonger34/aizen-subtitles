# -*- coding: utf-8 -*-
"""二次收紧: 补上图鉴/预告/演职员表关键词 + 批内去重(同集同句 ±6s 只留一条)。"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
keep = json.load(open(os.path.join(B, 'review', 'dense3_final.json'), encoding='utf-8'))

GUIDE2 = ('骨兽', '巨型生物', '传说', '哥莫拉', '格尔吉欧', '波恩', '空中型', '烈火形态', '跃水形态',
          '罗索', '布鲁', '泰罗', '赛文', '银河奥特曼', '迪迦', '欧布', '维克特利', '艾克斯', '赛罗',
          '雷德王', '金古桥', '达达', '剃刀', '巴萨', '伽玛', '玛伽', '必杀技', '使用多种技能',
          '进行作战', '水晶进行变身', '变身成为', '取得胜利', '商店街相模原', '福城', '相模原麻',
          '欢迎来到爱染科技')


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def score(a, b):
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return min(sum(1 for ch in a if ch in sb) / len(a), sum(1 for ch in b if ch in sa) / len(b))


out, drop = [], collections.Counter()
for v in sorted(keep, key=lambda x: (x['ep'], x['sec'])):
    t = cn(v['text'])
    if any(w in t for w in GUIDE2):
        drop['图鉴/预告/卡片'] += 1
        continue
    dup = next((o for o in out if o['ep'] == v['ep'] and abs(o['sec'] - v['sec']) <= 6
                and score(cn(o['text']), t) >= 0.9), None)
    if dup:
        drop['批内重复'] += 1
        continue
    out.append(v)
print('剔除:', dict(drop), ' 最终:', len(out))
json.dump(out, open(os.path.join(B, 'review', 'dense3_final2.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
byep = collections.Counter(v['ep'] for v in out)
print('每集条数:', dict(sorted(byep.items())))
for v in out[:40]:
    print(f"   {v['ep']} {v['t']:>7s}  [{v['text']}]")
