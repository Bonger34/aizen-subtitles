# -*- coding: utf-8 -*-
"""列出某集策展后的候选, 便于人工核对(默认 P25)。"""
import json
import os
import sys

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
ep = sys.argv[1] if len(sys.argv) > 1 else 'P25'
d = json.load(open(os.path.join(B, 'review', 'dense3_final2.json'), encoding='utf-8'))
rows = [v for v in d if v['ep'] == ep]
print(f'{ep}: {len(rows)} 条')
for v in sorted(rows, key=lambda x: x['sec']):
    print(f"   {v['t']:>7s}  [{v['text']}]")
