# -*- coding: utf-8 -*-
"""q_pick4.py — 把人工核对通过的"非互斥收回"候选写入 q_manual_verdicts.json 的 frame_apply。

白名单为 q_sheet4_*.jpg 的序号(37 条 apply_add 型候选中人工确认的 31 条);
另对 2 条做文本微调(去掉 OCR 带出的逗号 / 补回 T)。
用法: python q_pick4.py [--dry]
"""
import json
import os
import sys

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
KEEP = [1, 2, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
        25, 26, 27, 28, 29, 30, 31, 32, 33, 37]
OVERRIDE = {
    ('P16', '0m46s'): '你到底想做什么',
    ('P18', '7m28s'): '当感受到T恤上进发出的热情时',
}

d = json.load(open(os.path.join(REVIEW, 'q_unmatched_resolved.json'), encoding='utf-8'))
cands = [r for r in d['candidate'] if r.get('kind') == 'add']
new_items = []
for i, r in enumerate(cands, 1):
    if i not in KEEP:
        continue
    new = OVERRIDE.get((r['ep'], r['ts']), r.get('best_text'))
    new_items.append({'ep': r['ep'], 'ts': r['ts'], 'old': r['old'], 'new': new,
                      'why': f"非互斥窗口读数补全 (sim={r['best_sim_unexcl']:.2f})"})
print(f'候选 {len(cands)} 条 -> 采纳 {len(new_items)} 条')
for x in new_items:
    print(f"  {x['ep']} {x['ts']:>7s} [{x['old']}] -> [{x['new']}]")

if '--dry' in sys.argv:
    raise SystemExit('(预演, 未写入)')
p = os.path.join(REVIEW, 'q_manual_verdicts.json')
man = json.load(open(p, encoding='utf-8'))
have = {(x['ep'], x['ts']) for x in man.get('frame_apply', [])}
add = [x for x in new_items if (x['ep'], x['ts']) not in have]
man.setdefault('frame_apply', []).extend(add)
json.dump(man, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'已追加 {len(add)} 条到 review/q_manual_verdicts.json')
