# -*- coding: utf-8 -*-
"""q_tsread_merge.py — 把逐集的 q_tsread<tag>_<EP>.json 合并成 q_tsread<tag>.json。

q_tsread.py 只在全部集跑完时才写总表; 中途中断或只跑单集时用本脚本补齐总表。
用法: python q_tsread_merge.py [--tag v2]
"""
import json
import os
import re
import sys

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')


def main():
    tag = 'v2'
    if '--tag' in sys.argv:
        tag = sys.argv[sys.argv.index('--tag') + 1]
    pat = re.compile(rf'q_tsread{tag}_(P\d+)\.json')
    # q_tsread.py 里的 rows 是累加的, 所以每集文件都含前面各集的行 —— 必须按 (ep,ts) 去重
    merged, eps = {}, []
    for f in sorted(os.listdir(REVIEW)):
        m = pat.fullmatch(f)
        if not m:
            continue
        eps.append(m.group(1))
        for r in json.load(open(os.path.join(REVIEW, f), encoding='utf-8')):
            merged[(r['ep'], r['ts'])] = r
    rows = list(merged.values())
    out = os.path.join(REVIEW, f'q_tsread{tag}.json')
    json.dump(rows, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'合并 {len(eps)} 集 / 去重后 {len(rows)} 条 -> {out}')


if __name__ == '__main__':
    main()
