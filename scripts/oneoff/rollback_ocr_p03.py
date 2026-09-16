# -*- coding: utf-8 -*-
"""rollback_ocr_p03.py — 回滚全库复核误改（P03 水印污染）"""
import json
import os

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(BASE, 'subtitle_clean')
APPLIED = os.path.join(BASE, 'review', 'ocr_revision_applied.json')

applied = json.load(open(APPLIED, encoding='utf-8'))
by_ep = {}
for x in applied:
    by_ep.setdefault(x['ep'], []).append(x)

for ep, items in by_ep.items():
    fs = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')]
    if not fs:
        continue
    path = os.path.join(CLEAN, fs[0])
    data = json.load(open(path, encoding='utf-8'))
    by_ts = {}
    for x in items:
        by_ts[x['ts']] = x['from']
    n = 0
    for r in data:
        ts = r.get('timestamp')
        if ts in by_ts and r.get('text') != by_ts[ts]:
            r['text'] = by_ts[ts]
            n += 1
    json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{ep}: 回滚 {n} 条（原 to→from）')
