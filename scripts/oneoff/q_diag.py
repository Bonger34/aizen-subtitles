# -*- coding: utf-8 -*-
"""q_diag.py — 诊断时间线采样: 打印指定时间区间的采样点(白像素数/签名差异/是否触发OCR)。
用法: python q_diag.py P02 14 24
"""
import json
import os
import sys

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ep = sys.argv[1]
t0 = float(sys.argv[2])
t1 = float(sys.argv[3])
tl = json.load(open(os.path.join(B, 'review', f'q_timeline_{ep}.json'), encoding='utf-8'))
sel = [p for p in tl['points'] if t0 <= p['t'] <= t1]
print(f"{ep} t{t0}~{t1}: {len(sel)} 点 (step={tl['step']})")
for p in sel:
    seg = ''
    if p.get('segs'):
        seg = ' | '.join(f"y{s['y0']}-{s['y1']} bin[{s.get('bin', '')}] raw[{s.get('raw', '')}]"
                         for s in p['segs'])
    print(f"  t{p['t']:>7.2f} white={p['white']:>6d} diff={p['diff']:.4f} "
          f"ocr={str(p.get('ocr')):>5s} {seg}")
