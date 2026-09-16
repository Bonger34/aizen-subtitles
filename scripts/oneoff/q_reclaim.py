# -*- coding: utf-8 -*-
"""q_reclaim.py — 把"被邻条抢走事件"的假 unmatched 收回, 并按非互斥最佳读数重新分档。

q_align_tl 用互斥贪心分配(一个事件只归一个条目), 于是同一句字幕附近的相邻条目会拿不到事件,
被判成"无任何匹配"; 但按非互斥口径它们在窗口里其实读到了完全一致的文本。
用法: python q_reclaim.py
输出: review/q_unmatched_resolved.json
"""
import json
import os
import sys
from collections import Counter

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
d = json.load(open(os.path.join(REVIEW, 'q_diag2.json'), encoding='utf-8'))

CONFIRM, SRC_LO = 0.95, 0.55
buckets = {'confirmed': [], 'candidate': [], 'unknown': [], 'no_reading': []}
for r in d:
    s = r['best_sim_unexcl']
    if r['n_texts'] == 0:
        buckets['no_reading'].append(r)
    elif s >= CONFIRM:
        buckets['confirmed'].append(r)
    elif s >= SRC_LO:
        buckets['candidate'].append(r)
    else:
        buckets['unknown'].append(r)

print('收回结果:')
for k, v in buckets.items():
    print(f'  {len(v):5d}  {k}')
print('\n成因 × 收回:')
cross = Counter((r['cause'], 'confirmed' if r in buckets['confirmed'] else
                 'candidate' if r in buckets['candidate'] else
                 'no_reading' if r in buckets['no_reading'] else 'unknown') for r in d)
for (c, b), n in cross.most_common():
    print(f'  {n:5d}  [{b}] {c}')

print('\n-- candidate(非互斥读到部分匹配) 按编辑类型统计:')
import sys as _s
_s.path.insert(0, B)
from difflib import SequenceMatcher  # noqa: E402
import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import norm  # noqa: E402
kinds = Counter()
for r in buckets['candidate']:
    a, b = norm(r['old']), norm(r.get('best_text', ''))
    sm = SequenceMatcher(None, a, b, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
    ks = {o[0] for o in ops}
    k = 'same' if not ks else ('add' if ks == {'insert'} else
                               'del' if ks == {'delete'} else
                               'replace' if ks == {'replace'} else 'mixed')
    r['kind'] = k
    r['desc'] = ';'.join(f"{o[0]}:{a[o[1]:o[2]]}->{b[o[3]:o[4]]}" for o in ops)[:70]
    kinds[k] += 1
print(' ', dict(kinds))
print('\n-- candidate 中的 apply_add 型(纯插入, 方向可靠):')
n = 0
for r in buckets['candidate']:
    if r['kind'] == 'add':
        n += 1
        print(f"{n:3d}. {r['ep']} {r['ts']:>7s} sim={r['best_sim_unexcl']:.2f} {r['desc']}")
        print(f"      旧[{r['old']}]")
        print(f"      新[{r.get('best_text')}]")
print(f'共 {n} 条')

json.dump({k: v for k, v in buckets.items()},
          open(os.path.join(REVIEW, 'q_unmatched_resolved.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n输出: review/q_unmatched_resolved.json')
