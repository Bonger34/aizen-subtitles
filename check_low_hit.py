# -*- coding: utf-8 -*-
"""检查已知"带外字幕"的时间点是否落在 仅LOW 区间内(验证扫描的召回)。"""
import json
import os

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CASES = {'P17': [1444, 1448], 'P20': [1447, 1464], 'P21': [1450], 'P16': [147], 'P01': [116, 117]}
for ep, secs in CASES.items():
    p = os.path.join(B, 'review', 'ext_regions', f'{ep}.json')
    if not os.path.exists(p):
        print(f'{ep}: 尚未扫描')
        continue
    d = json.load(open(p, encoding='utf-8'))
    print(f'{ep}: 仅LOW {len(d["low_only"])} 段 / BAND {len(d["regions"]["BAND"])} 段')
    for s in secs:
        low = [x for x in d['low_only'] if x[0] - 1 <= s <= x[1] + 1]
        band = [x for x in d['regions']['BAND'] if x[0] - 1 <= s <= x[1] + 1]
        print(f'   {s // 60}m{s % 60:02d}s  仅LOW={low}  BAND={band}')
