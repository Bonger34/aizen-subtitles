# -*- coding: utf-8 -*-
"""修正 3 条"库文本掉了数字"的条目(配图画面已确认含该数字, 只改文本)。"""
import json
import os
import sys

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
FIX = [('P08', '12m26s', '年前绫香星从天而降', '1300年前绫香星从天而降'),
       ('P19', '11m25s', '周期为年的椭圆轨道', '周期为1300年的椭圆轨道'),
       ('P19', '11m44s', '然而那之后又过了年', '然而那之后又过了1300年')]

apply = '--apply' in sys.argv
for ep, ts, old, new in FIX:
    p = [os.path.join(CLEAN, f) for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    data = json.load(open(p, encoding='utf-8'))
    hit = 0
    for e in data:
        if e['timestamp'] == ts and (e.get('text') or '').strip() == old:
            e['text'] = new
            hit += 1
    print(f'  {ep} {ts}  [{old}] -> [{new}]  命中 {hit}')
    if apply and hit:
        json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('(已落盘)' if apply else '(预演)')
