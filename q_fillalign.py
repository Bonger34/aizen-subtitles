# -*- coding: utf-8 -*-
"""q_fillalign.py — 把窗口补扫(q_fill_<EP>.json)的读数与条目对齐并分档。

与 q_align_tl 同口径: 只有"新读数与旧文本高度相似"才说明读到同一句; 差异按编辑操作分型,
纯插入(add)方向可靠, 其余转人工。
用法: python q_fillalign.py [P01 P02 ...]
输出: review/q_fill_resolved.json
"""
import json
import os
import re
import sys
from collections import Counter
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q_common import kana_ratio, norm, sim, to_simp  # noqa: E402

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
CONFIRM, SRC_LO = 0.95, 0.55


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def edit_kind(old, new):
    a, b = norm(old), norm(new)
    sm = SequenceMatcher(None, a, b, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
    ks = {o[0] for o in ops}
    desc = ';'.join(f"{o[0]}:{a[o[1]:o[2]]}->{b[o[3]:o[4]]}" for o in ops)[:70]
    if not ks:
        return 'same', desc
    if ks == {'insert'}:
        return 'add', desc
    if ks == {'delete'}:
        return 'del', desc
    if ks == {'replace'}:
        return 'replace', desc
    return 'mixed', desc


def main():
    eps = [a for a in sys.argv[1:] if not a.startswith('-')] or None
    res = json.load(open(os.path.join(REVIEW, 'q_unmatched_resolved.json'), encoding='utf-8'))
    todo = res['unknown'] + res['no_reading']
    by_ep = {}
    for r in todo:
        by_ep.setdefault(r['ep'], []).append(r)

    out, kinds = [], Counter()
    n_conf = n_cand = n_unk = 0
    for ep in sorted(by_ep):
        if eps and ep not in eps:
            continue
        p = os.path.join(REVIEW, f'q_fill_{ep}.json')
        if not os.path.exists(p):
            continue
        fill = json.load(open(p, encoding='utf-8'))
        paths = fill.get('paths', ['bin', 'raw'])
        pts = [q for q in fill['points'] if q.get('segs')]
        for r in by_ep[ep]:
            sec = parse_ts(r['ts'])
            if sec is None:
                continue
            inw = [q for q in pts if abs(q['t'] - sec) <= 3.5]
            texts = [to_simp(s.get(pp, '')) for q in inw for s in q['segs'] for pp in paths]
            scored = sorted(((sim(t, r['old']), t) for t in texts if t), key=lambda z: -z[0])
            best, best_text = (scored[0] if scored else (0.0, ''))
            rec = dict(r, best_sim_fill=round(best, 3), best_text=best_text,
                       n_pts_fill=len(inw), n_read=len(texts))
            if best >= CONFIRM:
                rec['verdict'] = 'confirmed'
                n_conf += 1
            elif best >= SRC_LO:
                k, desc = edit_kind(r['old'], best_text)
                rec.update(kind=k, desc=desc, kana=round(kana_ratio(best_text), 2))
                kinds[k] += 1
                if k == 'add' and rec['kana'] <= 0.15:
                    rec['verdict'] = 'apply_add'
                else:
                    rec['verdict'] = 'review'
                n_cand += 1
            else:
                rec['verdict'] = 'unknown'
                n_unk += 1
            out.append(rec)
    print(f'补扫对齐 {len(out)} 条: confirmed {n_conf} / 候选 {n_cand} {dict(kinds)} / '
          f'仍未知 {n_unk}')
    json.dump(out, open(os.path.join(REVIEW, 'q_fill_resolved.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('输出: review/q_fill_resolved.json')
    for r in out:
        if r['verdict'] == 'apply_add':
            print(f"  {r['ep']} {r['ts']:>7s} sim={r['best_sim_fill']:.2f} {r['desc']}")
            print(f"      旧[{r['old']}]")
            print(f"      新[{r['best_text']}]")


if __name__ == '__main__':
    main()
