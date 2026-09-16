# -*- coding: utf-8 -*-
"""q_targets.py — 汇总"仍未澄清"的条目清单, 供逐帧视频扫描使用。

未澄清 = 1368 条 unmatched 中, 扣掉:
  * 画面已证实旧文本的(非互斥 202 + 帧图 436 + 部分证实 49)
  * 本轮已修正并落盘的(取 review/q_manual_verdicts.json 的 frame_apply + q_apply_result.json)
用法: python q_targets.py
输出: review/q_targets.json + 控制台统计
"""
import json
import os
from collections import Counter

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')


def load(name, key=None):
    p = os.path.join(REVIEW, name)
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding='utf-8'))
    return d[key] if key else d


def main():
    unres = load('q_unmatched_resolved.json')
    final = load('q_final.json')                 # 1056 条帧图验证(含 band)
    partial = load('q_partial.json')             # 读不出档的字符子集分档
    man = load('q_manual_verdicts.json') or {}
    applied = load('q_apply_result.json') or {'applied': []}

    fixed = {(x['ep'], x['ts']) for x in man.get('frame_apply', [])}
    fixed |= {(x['ep'], x['ts']) for x in applied.get('applied', [])}
    part_ok = {(r['ep'], r['ts']) for r in partial['partial']}
    frame_ok = {(r['ep'], r['ts']) for r in final if r['band'] == 'frame_confirmed'}
    unexcl_ok = {(r['ep'], r['ts']) for r in unres['confirmed']}

    targets, seen = [], set()

    def add(r, why):
        k = (r['ep'], r['ts'])
        if k in seen or k in fixed or k in part_ok or k in frame_ok or k in unexcl_ok:
            return
        seen.add(k)
        targets.append({'ep': r['ep'], 'ts': r['ts'], 'old': r['old'], 'why': why})

    for r in unres['candidate']:
        add(r, 'unexcl_candidate')
    for r in final:
        if r['band'] in ('candidate', 'weak'):
            add(r, f"frame_{r['band']}")
        elif r['band'] == 'unreadable':
            add(r, 'frame_unreadable')
    for r in unres['unknown'] + unres['no_reading']:
        add(r, 'no_reading')

    c = Counter(t['why'] for t in targets)
    print(f'未澄清 {len(targets)} 条')
    for k, v in c.most_common():
        print(f'  {v:5d}  {k}')
    print('按集:', dict(sorted(Counter(t['ep'] for t in targets).items())))
    json.dump(targets, open(os.path.join(REVIEW, 'q_targets.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('输出: review/q_targets.json')


if __name__ == '__main__':
    main()
