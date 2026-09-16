# -*- coding: utf-8 -*-
"""q_pick3.py — 从 unmatched 里筛"补数字/字母"型候选: 时间线读到的文本比旧文本多出数字或拉丁字母。

这类差异方向可靠(旧文本缺了画面上的数字/字母), 与 apply_add 同理, 但整体相似度低
(错字/漏字多) 落到了 unmatched 档, 需要单独捞。
用法: python q_pick3.py
"""
import json
import os
import re
import sys
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import kana_ratio, norm, sim  # noqa: E402

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALNUM = set('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
d = json.load(open(os.path.join(B, 'review', 'q_align_tl.json'), encoding='utf-8'))
rows = []
for ep in sorted(d):
    for r in d[ep]['items']:
        if r['verdict'] != 'unmatched' or not r.get('new'):
            continue
        a, b = norm(r['old']), norm(r['new'])
        if len(b) <= len(a):
            continue
        extra = set(b) - set(a)
        if not (extra & ALNUM):
            continue
        if kana_ratio(b) > 0.15:
            continue
        sm = SequenceMatcher(None, a, b, autojunk=False)
        ops = [f"{o[0]}:{a[o[1]:o[2]]}->{b[o[3]:o[4]]}" for o in sm.get_opcodes() if o[0] != 'equal']
        rows.append({'ep': ep, 'ts': r['ts'], 'old': r['old'], 'new': r['new'],
                     'sim': r['best_sim'], 'sup': r.get('support'), 'dt': r.get('dt'),
                     'desc': ';'.join(ops)[:80], 'dlen': len(b) - len(a)})
print(f'候选 {len(rows)} 条')
for i, r in enumerate(rows, 1):
    print(f"{i:3d}. {r['ep']} {r['ts']:>7s} sim={r['sim']:.2f} sup={r['sup']} dt={r['dt']:+.2f}s "
          f"+{r['dlen']} {r['desc']}")
    print(f"     旧[{r['old']}]")
    print(f"     新[{r['new']}]")
json.dump(rows, open(os.path.join(B, 'review', 'q_pick3.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
