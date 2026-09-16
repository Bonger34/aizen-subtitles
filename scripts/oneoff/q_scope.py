# -*- coding: utf-8 -*-
"""q_scope.py — 统计未澄清条目的时间分布, 区分"正片台词"与"片头/片尾非台词段"。

用途: 未澄清条目里相当一部分落在片尾演职员表/版权卡段(旧口径: 只算台词字幕), 需要分开计数,
否则会把"非台词"混进"未澄清的台词"里, 高估残留风险。
用法: python q_scope.py
"""
import json
import os
import re
from collections import Counter

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
TAIL = 21 * 60 + 30      # 片尾段起点(保守)
HEAD = 1 * 60 + 30       # 片头版权卡/标题段


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def bucket(sec):
    if sec is None:
        return '未知'
    if sec >= TAIL:
        return '片尾段(>=21m30s)'
    if sec <= HEAD:
        return '片头段(<=1m30s)'
    return '正片'


for name in ('q_targets.json', 'q_fill_resolved.json'):
    p = os.path.join(REVIEW, name)
    if not os.path.exists(p):
        continue
    d = json.load(open(p, encoding='utf-8'))
    c = Counter(bucket(parse_ts(r['ts'])) for r in d)
    print(f'{name}: {len(d)} 条')
    for k, v in c.most_common():
        print(f'   {v:5d}  {k}')
    if 'verdict' in (d[0] if d else {}):
        cross = Counter((bucket(parse_ts(r['ts'])), r['verdict']) for r in d)
        print('   交叉:', dict(sorted(cross.items())))
    print()
