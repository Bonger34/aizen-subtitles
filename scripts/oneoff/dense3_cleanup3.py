# -*- coding: utf-8 -*-
"""按文本删除残留垃圾条目(不依赖时间戳)。"""
import json
import os
import sys

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
DEL = {'你然在想这个', '手島光仕上行', '深藏的那句谢谢',
       '倉田友衣子阿部早夏子谷勇介稻木电人', '日喂差多了好吧',
       '该小组由负责灾后重建的官员带领', '全部都得',
       '行手大一现如今一用淘气的眼神发出信号', '集全世界都在等着我'}

apply = '--apply' in sys.argv
tot = 0
for fn in sorted(os.listdir(CLEAN)):
    if not fn.endswith('.json'):
        continue
    p = os.path.join(CLEAN, fn)
    data = json.load(open(p, encoding='utf-8'))
    n0 = len(data)
    data = [e for e in data if (e.get('text') or '').strip() not in DEL]
    if len(data) != n0:
        print(f'  {fn[1:4]}: {n0} -> {len(data)}  删除 {[e.get("text") for e in json.load(open(p, encoding="utf-8")) if (e.get("text") or "").strip() in DEL]}')
        tot += n0 - len(data)
        if apply:
            json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'共删除 {tot} 条' + ('(已落盘)' if apply else '(预演)'))
