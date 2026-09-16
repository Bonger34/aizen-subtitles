# -*- coding: utf-8 -*-
"""补做: 删除 8 条残留垃圾条目, 修正 2 处带杂字前缀的文本。"""
import json
import os
import sys

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
DEL = [('P03', '0m15s', '你然在想这个'),
       ('P08', '23m00s', '手島光仕上行'),
       ('P09', '23m09s', '深藏的那句谢谢'),
       ('P14', '22m47s', '倉田友衣子阿部早夏子谷勇介稻木电人'),
       ('P15', '0m10s', '日喂差多了好吧'),
       ('P15', '5m45s', '该小组由负责灾后重建的官员带领'),
       ('P20', '20m50s', '全部都得'),
       ('P22', '22m57s', '行手大一现如今一用淘气的眼神发出信号')]
FIX = [('P08', '3m35s', '集全世界都在等着我', '全世界都在等着我'),
       ('P18', '7m09s', '見見驚感動那种惊讶和感动', '那种惊讶和感动')]

apply = '--apply' in sys.argv
for ep in sorted({d[0] for d in DEL} | {f[0] for f in FIX}):
    p = [os.path.join(CLEAN, f) for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    data = json.load(open(p, encoding='utf-8'))
    n0 = len(data)
    data = [e for e in data
            if not any(e['timestamp'] == ts and (e.get('text') or '').strip() == tx
                       for ep2, ts, tx in DEL if ep2 == ep)]
    for ep2, ts, old, new in FIX:
        if ep2 != ep:
            continue
        for e in data:
            if e['timestamp'] == ts and (e.get('text') or '').strip() == old:
                e['text'] = new
                print(f'  修正 {ep} {ts} [{old}] -> [{new}]')
    print(f'  {ep}: {n0} -> {len(data)}')
    if apply:
        json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('(已落盘)' if apply else '(预演)')
