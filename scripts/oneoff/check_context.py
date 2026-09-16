# -*- coding: utf-8 -*-
"""check_context.py — 跨数据源核查 P06/P19 争议条目上下文"""
import json
import os

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'


def sec(ts):
    m = ts.split('m')
    return int(m[0]) * 60 + int(m[1].rstrip('s'))


def dump(dirs, ep, lo, hi):
    print('===', ep, '===')
    for d in dirs:
        p = os.path.join(BASE, d)
        if not os.path.isdir(p):
            print('(missing)', d)
            continue
        fs = [f for f in os.listdir(p) if f.startswith(f'[{ep}]') and f.endswith('.json')]
        if not fs:
            print('(no file)', d)
            continue
        data = json.load(open(os.path.join(p, fs[0]), encoding='utf-8'))
        rows = sorted([r for r in data if lo <= sec(r.get('timestamp', '0m0s')) <= hi],
                      key=lambda r: sec(r['timestamp']))
        print('--', d)
        for r in rows:
            print(f"   {r['timestamp']:>7}  {r['text'][:44]}")


dump(['subtitle', 'subtitle_paddle_v5', 'vl_out', 'subtitle_clean'], 'P06', 1305, 1325)
dump(['subtitle', 'subtitle_paddle_v5', 'vl_out', 'subtitle_clean'], 'P19', 1145, 1165)
