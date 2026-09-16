# -*- coding: utf-8 -*-
"""全库检索窗口扫描读到的句子, 判断是真缺还是已收录(可能记在别的时间点)。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
Q = ['休想得逞', '勇海我们上', '明白发射牵引光束', '发射牵引光束', '将你和这颗星球一起一起炸毁',
     '这是最后的水晶了', '那家伙又想吸取光之轨迹']


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff]', '', s or '')


rows = []
for fn in sorted(os.listdir(CLEAN)):
    if not fn.endswith('.json'):
        continue
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        rows.append((fn[1:4], e['timestamp'], e.get('text') or ''))

for q in Q:
    key = cn(q)
    hits = [(ep, ts, tx) for ep, ts, tx in rows if key in cn(tx)]
    print(f'[{"有" if hits else "★无★"}] 「{q}」 命中 {len(hits)}')
    for ep, ts, tx in hits[:4]:
        print(f'      {ep} {ts}  {tx}')
    if not hits:
        # 退一步: 逐字包含度
        best = sorted(((sum(1 for c in key if c in cn(tx)) / len(key), ep, ts, tx)
                       for ep, ts, tx in rows), reverse=True)[:3]
        for sc, ep, ts, tx in best:
            print(f'      最相近 分{sc:.2f}: {ep} {ts}  {tx}')
