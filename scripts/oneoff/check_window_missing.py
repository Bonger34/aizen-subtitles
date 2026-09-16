# -*- coding: utf-8 -*-
"""核实窗口扫描发现"库中缺失"的几句: 打印库中对应时段的条目, 看是否真的缺。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
CASES = [('P22', 16 * 60 + 0, 16 * 60 + 12, '休想得逞'),
         ('P22', 16 * 60 + 45, 16 * 60 + 56, '勇海我们上'),
         ('P24', 17 * 60 + 10, 17 * 60 + 40, '明白发射牵引光束 / 将你和这颗星球一起炸毁'),
         ('P24', 18 * 60 + 0, 18 * 60 + 10, '这是最后的水晶了')]


def sec_of(t):
    m = re.match(r'(\d+)m(\d+)s', t)
    return int(m.group(1)) * 60 + int(m.group(2))


for ep, lo, hi, note in CASES:
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    rows = [(sec_of(e['timestamp']), e['timestamp'], e.get('text'))
            for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))]
    print(f'--- {ep} {lo // 60}m{lo % 60:02d}s~{hi // 60}m{hi % 60:02d}s  窗口扫描读到: {note}')
    got = [r for r in rows if lo <= r[0] <= hi]
    if not got:
        print('    (库中该时段完全无条目)')
    for s, ts, tx in got:
        print(f'    {ts:>7s}  {tx}')
    print()
