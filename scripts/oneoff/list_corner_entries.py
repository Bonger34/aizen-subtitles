# -*- coding: utf-8 -*-
"""列出 P18「情熱行星」对谈段与 P11「图鉴」对谈段的库条目, 标出疑似碎片。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
WIN = [('P18', 7 * 60 + 50, 9 * 60 + 40), ('P11', 9 * 60 + 55, 10 * 60 + 20)]

for ep, lo, hi in WIN:
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    print(f'--- {ep} {lo // 60}m{lo % 60:02d}s ~ {hi // 60}m{hi % 60:02d}s')
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        m = re.match(r'(\d+)m(\d+)s', e['timestamp'])
        s = int(m.group(1)) * 60 + int(m.group(2))
        if not lo <= s <= hi:
            continue
        n = re.sub(r'[^\u4e00-\u9fff]', '', e.get('text') or '')
        flag = '  <== 疑似碎片' if len(n) <= 3 else ''
        print(f"   {e['timestamp']:>7s}  [{e.get('text')}]{flag}")
