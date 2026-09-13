# -*- coding: utf-8 -*-
"""q_diag3.py — 诊断逐帧扫描为何仍读不到: 打印目标条目窗口内的白像素/触发/读数情况。
用法: python q_diag3.py P01 [目标条数=6]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q_common import sim  # noqa: E402

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


ep = sys.argv[1]
n_show = int(sys.argv[2]) if len(sys.argv) > 2 else 6
targets = [r for r in json.load(open(os.path.join(REVIEW, 'q_targets.json'), encoding='utf-8'))
           if r['ep'] == ep]
d = json.load(open(os.path.join(REVIEW, f'q_fill_{ep}.json'), encoding='utf-8'))
pts = d['points']
paths = d.get('paths', ['bin', 'raw'])
print(f"{ep}: {len(targets)} 个目标 / 采样 {len(pts)} 点 / OCR {d['n_ocr']} 次")
for r in targets[:n_show]:
    sec = parse_ts(r['ts'])
    inw = [p for p in pts if abs(p['t'] - sec) <= 4.0]
    nz = [p for p in inw if p['white'] > 0]
    oc = [p for p in inw if p.get('ocr')]
    texts = [s.get(pp, '') for p in oc for s in p['segs'] for pp in paths]
    best = max([sim(t, r['old']) for t in texts] or [0.0])
    print(f"  {r['ts']:>7s} 旧[{r['old'][:22]}] 采样{len(inw)} 有白{len(nz)} OCR{len(oc)} "
          f"最佳={best:.2f}")
    if nz:
        ws = sorted(p['white'] for p in nz)
        print(f"          窗口内白像素数: 最小{ws[0]} 中位{ws[len(ws) // 2]} 最大{ws[-1]}")
    if texts:
        print(f"          读数样例: {[t for t in texts if t][:5]}")
