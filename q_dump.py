# -*- coding: utf-8 -*-
"""q_dump.py — 打印时间线事件/采样点分布, 用于诊断重扫覆盖情况。
用法: python q_dump.py P02 [事件数=80] [--pts]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q_align_tl import build_events  # noqa: E402

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')

ep = sys.argv[1]
nmax = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 80
tl = json.load(open(os.path.join(REVIEW, f'q_timeline_{ep}.json'), encoding='utf-8'))
pts = tl['points']
ocr_pts = [p for p in pts if p.get('ocr')]
print(f"{ep}: 采样 {len(pts)} 点(step={tl['step']}) / OCR {len(ocr_pts)} 点 / "
      f"有字幕签名点 {sum(1 for p in pts if p['white'] > 0)} / {tl['elapsed']}s")
if '--pts' in sys.argv:
    for p in pts[:nmax]:
        print(f"  t{p['t']:>7.2f} white={p['white']:>5d} diff={p['diff']:.4f} ocr={p.get('ocr')}")
else:
    ev = build_events(tl, tl['paths'])
    print(f'事件 {len(ev)}')
    for e in ev[:nmax]:
        print(f"  t{e['mid']:>7.2f} [{e['text']}] n={e['n_read']} pts={e['n_pts']}")
