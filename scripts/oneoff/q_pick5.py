# -*- coding: utf-8 -*-
"""q_pick5.py — 把帧图验证中人工确认的修正写入 q_manual_verdicts.json 的 frame_apply。

白名单为 review/q_sheet6_*.jpg 的序号(candidate+weak 共 84 条中确认的 27 条);
另对 2 条做文本微调(阿->啊 / 去掉尾部冒号)。
用法: python q_pick5.py [--dry]
"""
import json
import os
import sys

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
KEEP = [2, 3, 4, 5, 9, 12, 14, 16, 18, 22, 24, 26, 29, 35, 36, 38, 43, 44, 51, 52, 54, 56,
        62, 66, 68, 69, 70]
OVERRIDE = {5: '加油啊', 56: '好不好小剑'}

items = json.load(open(os.path.join(REVIEW, 'q_final.json'), encoding='utf-8'))
rows = [r for r in items if r['band'] in ('candidate', 'weak')]
new_items = []
for i, r in enumerate(rows, 1):
    if i not in KEEP:
        continue
    new_items.append({'ep': r['ep'], 'ts': r['ts'], 'old': r['old'],
                      'new': OVERRIDE.get(i, r.get('frame_text')),
                      'why': f"帧图验证确认 (sim={r['sim_old']:.2f}, {r['kind']})"})
print(f'候选 {len(rows)} 条 -> 采纳 {len(new_items)} 条')
for x in new_items:
    print(f"  {x['ep']} {x['ts']:>7s} [{x['old']}] -> [{x['new']}]")
if '--dry' in sys.argv:
    raise SystemExit('(预演)')
p = os.path.join(REVIEW, 'q_manual_verdicts.json')
man = json.load(open(p, encoding='utf-8'))
have = {(x['ep'], x['ts']) for x in man.get('frame_apply', [])}
add = [x for x in new_items if (x['ep'], x['ts']) not in have]
man.setdefault('frame_apply', []).extend(add)
json.dump(man, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'已追加 {len(add)} 条')
