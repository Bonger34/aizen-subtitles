# -*- coding: utf-8 -*-
"""最后一轮清理: 删除歌词碎片条目, 修正一条被截断的文本。"""
import json
import os
import sys

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
DEL = ['信抜', '咽心', '起喊快乐', '旋风', '可是']
FIX = [('P23', '气毁灭它', '一口气毁灭它')]

apply = '--apply' in sys.argv
tot_del = tot_fix = 0
for fn in sorted(os.listdir(CLEAN)):
    if not fn.endswith('.json'):
        continue
    p = os.path.join(CLEAN, fn)
    data = json.load(open(p, encoding='utf-8'))
    n0 = len(data)
    data = [e for e in data if (e.get('text') or '').strip() not in DEL]
    d = n0 - len(data)
    f = 0
    for ep, old, new in FIX:
        if not fn.startswith(f'[{ep}]'):
            continue
        for e in data:
            if (e.get('text') or '').strip() == old:
                e['text'] = new
                f += 1
    if d or f:
        print(f'  {fn[:5]}: 删除 {d}, 修正 {f}')
        tot_del += d
        tot_fix += f
        if apply:
            json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'共删除 {tot_del}, 修正 {tot_fix}' + ('(已落盘)' if apply else '(预演)'))
