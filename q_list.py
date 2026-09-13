# -*- coding: utf-8 -*-
"""q_list.py — 按判定类型列出条目(默认 apply_add), 便于逐条人工核对。
用法: python q_list.py [apply_add] [--sep] 
"""
import json
import os
import sys

B = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(B, 'review', 'q_align_tl.json'), encoding='utf-8'))
want = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'apply_add'
sep = '--sep' in sys.argv
n = 0
for ep in sorted(d):
    for r in d[ep]['items']:
        if r.get('verdict') == want:
            n += 1
            dt = r.get('dt')
            print(f"{n:3d}. {ep} {r['ts']:>7s} sim={r['best_sim']:.2f} sup={r.get('support')} "
                  f"dt={dt:+.2f}s {r.get('desc', '')}")
            print(f"     旧 [{r['old']}]")
            print(f"     新 [{r['new']}]")
            if sep:
                print('     ' + '-' * 60)
if not n:
    print(f'(没有 {want} 类型条目)')
