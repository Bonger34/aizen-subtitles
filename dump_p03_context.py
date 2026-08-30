# -*- coding: utf-8 -*-
"""dump_p03_context.py — 导出 P03 7m00-7m30 字幕条目供修订"""
import json

P = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\subtitle_clean\[P03]3 欢迎来到爱染科技.json'
OUT = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\review\p03_7m12s_context.txt'

d = json.load(open(P, encoding='utf-8'))


def sec(ts):
    m = ts.split('m')
    return int(m[0]) * 60 + int(m[1].rstrip('s'))


items = sorted([r for r in d if 420 <= sec(r['timestamp']) <= 445],
               key=lambda r: sec(r['timestamp']))
with open(OUT, 'w', encoding='utf-8') as f:
    for r in items:
        f.write(f"{r['timestamp']:>8}  {r['text']}\n")
print('written', len(items))
