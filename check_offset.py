# -*- coding: utf-8 -*-
"""check_offset.py — 检查已补录条目的时间戳偏移"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(BASE, 'subtitle_clean')
REVIEW = os.path.join(BASE, 'review')

reals = json.load(open(os.path.join(REVIEW, 'gap_real.json'), encoding='utf-8'))


def ts_sec(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2))


for ep in sorted(reals.keys()):
    f = [x for x in os.listdir(CLEAN) if x.startswith(f'[{ep}]') and x.endswith('.json')][0]
    arr = json.load(open(os.path.join(CLEAN, f), encoding='utf-8'))
    for r in reals[ep]:
        hits = [(e['timestamp'], e['text']) for e in arr if e['text'] == r['text']]
        for ts, tx in hits:
            off = ts_sec(ts) - ts_sec(r['t'])
            print(f'{ep} 扫描 {r["t"]} -> 库 {ts} (偏移 {off:+d}s) [{tx}]')
