# -*- coding: utf-8 -*-
"""删除 2 条噪声条目(P22 17m53s「口」/ P24 18m11s「敬告」)。

注意: 这两条当前指向的是与他人共用的配图帧(P22_17m50s.jpg / P24_18m14s.jpg),
      该帧仍被邻条使用, 因此只删条目, 不动帧文件。
"""
import json
import os
import sys

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
TARGETS = [('P22', '17m53s', '口'), ('P24', '18m11s', '敬告')]

apply = '--apply' in sys.argv
for ep, ts, text in TARGETS:
    p = [os.path.join(CLEAN, f) for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    data = json.load(open(p, encoding='utf-8'))
    before = len(data)
    kept = [e for e in data if not (e['timestamp'] == ts and (e.get('text') or '').strip() == text)]
    print(f'  {ep} {ts} [{text}]  {before} -> {len(kept)}')
    if apply and len(kept) != before:
        json.dump(kept, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('(已落盘)' if apply else '(预演)')
