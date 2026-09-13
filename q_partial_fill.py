# -*- coding: utf-8 -*-
"""q_partial_fill.py — 从"部分证实"里筛补全型候选: 旧文本是帧图读数的子序列, 且帧读更长。

与 apply_add 同理(旧文本字符全保留 + 新读数多出字符), 方向可靠; 但仍需人工看图确认
多出的字符是字幕内容还是帧计数器/画面文字。
用法: python q_partial_fill.py
输出: review/q_partial_fill.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q_common import norm  # noqa: E402

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')


def is_subseq(a, b):
    it = iter(b)
    return all(c in it for c in a)


d = json.load(open(os.path.join(REVIEW, 'q_partial.json'), encoding='utf-8'))
rows = []
for r in d['partial']:
    a, b = norm(r['old']), norm(r.get('frame_text') or '')
    if len(b) > len(a) and is_subseq(a, b):
        r['desc'] = f'补全 +{len(b) - len(a)}'
        rows.append(r)
print(f'补全型候选 {len(rows)} 条')
for r in rows:
    print(f"  {r['ep']} {r['ts']:>7s} [{r['old']}] -> [{r['frame_text']}]")
json.dump(rows, open(os.path.join(REVIEW, 'q_partial_fill.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('输出: review/q_partial_fill.json')
