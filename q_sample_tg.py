# -*- coding: utf-8 -*-
"""q_sample_tg.py — 从全库随机抽样若干条目, 用于估计"库文本 vs 画面"的整体一致率。

排除已跑过的两组(623 未澄清目标 / 206 奥特曼名称条目), 避免重复劳动。
固定随机种子保证可复现。
用法: python q_sample_tg.py [样本量=400]
输出: review/q_sample_tg.json
"""
import json
import os
import random
import re
import sys

B = os.path.dirname(os.path.abspath(__file__))
CLEAN = os.path.join(B, 'subtitle_clean')
REVIEW = os.path.join(B, 'review')
SEED = 20260913


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    done = set()
    for fn in ('q_targets.json', 'q_names_tg.json'):
        p = os.path.join(REVIEW, fn)
        if os.path.exists(p):
            done |= {(r['ep'], r['ts']) for r in json.load(open(p, encoding='utf-8'))}
    pool = []
    for f in sorted(os.listdir(CLEAN)):
        if not (f.endswith('.json') and re.match(r'^\[P(0[1-9]|1[0-9]|2[0-5])\]', f)):
            continue
        ep = re.search(r'\[(P\d+)\]', f).group(1)
        for e in json.load(open(os.path.join(CLEAN, f), encoding='utf-8')):
            ts, t = e.get('timestamp'), e.get('text', '')
            if ts and t and (ep, ts) not in done:
                pool.append({'ep': ep, 'ts': ts, 'old': t, 'why': 'sample'})
    random.seed(SEED)
    pick = random.sample(pool, min(n, len(pool)))
    pick.sort(key=lambda r: (r['ep'], r['ts']))
    json.dump(pick, open(os.path.join(REVIEW, 'q_sample_tg.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'候选池 {len(pool)} 条, 抽样 {len(pick)} 条 -> review/q_sample_tg.json (seed={SEED})')
    from collections import Counter
    print('按集:', dict(sorted(Counter(r['ep'] for r in pick).items())))


if __name__ == '__main__':
    main()
