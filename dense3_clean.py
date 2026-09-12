# -*- coding: utf-8 -*-
"""最终清理: 手工剔除残留的片尾职员表/歌词/新闻画面文字, 并清理个别杂字前缀。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
SRC = os.path.join(B, 'review', 'dense3_add.json')
cands = json.load(open(SRC, encoding='utf-8'))

DROP = [('P03', '0m15s', '你然在想这个'),            # 同秒重复(错读版)
        ('P08', '23m00s', '手島光仕上行'),            # 片尾职员表
        ('P09', '23m09s', '深藏的那句谢谢'),           # 片尾歌词
        ('P14', '22m47s', '倉田友衣子阿部早夏子谷勇介稻木电人'),
        ('P15', '0m10s', '日喂差多了好吧'),            # 与 0m09s 重复
        ('P15', '5m45s', '该小组由负责灾后重建的官员带领'),   # 新闻画面文字
        ('P20', '20m50s', '全部都得'),                # 20m49s 已有完整句
        ('P22', '22m57s', '行手大一现如今一用淘气的眼神发出信号'),
        ('P18', '22m00s', '快住手啊爸爸')]            # 与 P19 的说法重复? 保留判断: 先留

DROP = [d for d in DROP if not (d[0] == 'P18' and d[2] == '快住手啊爸爸')]
FIX = {('P08', '3m35s'): '全世界都在等着我',
       ('P18', '7m09s'): '那种惊讶和感动'}

out = []
for c in cands:
    if any(c['ep'] == ep and c['t'] == ts and c['text'] == tx for ep, ts, tx in DROP):
        continue
    fix = FIX.get((c['ep'], c['t']))
    if fix:
        c = {**c, 'text': fix}
    out.append(c)
print(f'清理 {len(cands)} -> {len(out)}')
json.dump(out, open(SRC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
