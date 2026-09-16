# -*- coding: utf-8 -*-
"""q_final.py — 汇总帧图验证(q_verifyall.json)结果: 分档 + 列出可能的文本修正。

分档:
  frame_confirmed  sim>=0.90  帧图读出与旧文本基本一致 -> 旧文本成立
  candidate        0.55~0.90 帧图读到相近但有差异     -> 看编辑类型
  weak             0.35~0.55 差异较大                 -> 可能是错字修正
  unreadable       <0.35     帧图读不出相关内容
用法: python q_final.py [--list weak|candidate]
输出: review/q_final.json + 控制台清单
"""
import json
import os
import sys
from collections import Counter
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import kana_ratio, norm, sim  # noqa: E402

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')


def edit_kind(old, new):
    a, b = norm(old), norm(new)
    sm = SequenceMatcher(None, a, b, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
    ks = {o[0] for o in ops}
    desc = ';'.join(f"{o[0]}:{a[o[1]:o[2]]}->{b[o[3]:o[4]]}" for o in ops)[:70]
    if not ks:
        return 'same', desc
    for k, s in (('add', {'insert'}), ('del', {'delete'}), ('replace', {'replace'})):
        if ks == s:
            return k, desc
    return 'mixed', desc


def main():
    items = json.load(open(os.path.join(REVIEW, 'q_verifyall.json'), encoding='utf-8'))['items']
    for r in items:
        s = r['sim_old']
        r['band'] = ('frame_confirmed' if s >= 0.90 else 'candidate' if s >= 0.55 else
                     'weak' if s >= 0.35 else 'unreadable')
        r['kind'], r['desc'] = edit_kind(r['old'], r.get('frame_text') or '')
        r['kana'] = round(kana_ratio(r.get('frame_text') or ''), 2)
    bands = Counter(r['band'] for r in items)
    print(f'共 {len(items)} 条: ' + ' | '.join(f'{k} {v}' for k, v in bands.items()))
    print('候选档编辑类型:',
          dict(Counter(r['kind'] for r in items if r['band'] in ('candidate', 'weak'))))
    json.dump(items, open(os.path.join(REVIEW, 'q_final.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    want = sys.argv[sys.argv.index('--list') + 1] if '--list' in sys.argv else None
    if want:
        sel = [r for r in items if r['band'] == want]
        print(f'\n=== {want} ({len(sel)} 条) ===')
        for i, r in enumerate(sel, 1):
            print(f"{i:3d}. {r['ep']} {r['ts']:>7s} sim={r['sim_old']:.2f} [{r['kind']}] {r['desc']}")
            print(f"      旧[{r['old']}]")
            print(f"      帧[{r.get('frame_text')}]")


if __name__ == '__main__':
    main()
