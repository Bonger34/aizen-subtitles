# -*- coding: utf-8 -*-
"""导出 A 组全部判定, 并筛出 OCR 含中文台词特征的帧供目视核查。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
d = json.load(open(os.path.join(B, 'review', 'orphan_ocr.json'), encoding='utf-8'))

lines = ['A 组 165 帧逐条判定(按帧名排序)']
for x in sorted(d['A'], key=lambda y: y['f']):
    lines.append(f"  {x['f']:18s} wr={x['wr']:.3f} {x.get('verdict', '?'):28s} ocr=[{x['ocr']}]")
open(os.path.join(B, 'review', 'A_verdicts.txt'), 'w', encoding='utf-8').write('\n'.join(lines))

# 中文台词特征: 含常用汉字词且不含假名; 用"该文本是否与任一库条目的中文相似度高"反向排除
# 这里改用简单判据: OCR 中不含片尾职员表的典型姓氏块
CREDIT = ('岡本', '坂井', '島田', '及川', '青井', '万理子', '渡', '野田', '有紗', '谷堂', '百貨',
          '長谷川', '哲久', '三好', '智紀', '鎌田', '比古', '芳賀', '神野', '貴嗣', '小酒井',
          '面川', '忠久', '勝又', '拓海', '小船', '有紀子', '広報', '宣伝', '李野', '北澤',
          '淳子', '吉村', '尚志', '竹田', '聡', '富十', '和泉', '原田', '笙太', '林工務店',
          '日本映像', '東宝', '株式会社', '映像', '照明', '制作', '監督', '助監督', '特撮')
sus = []
for x in d['A'] + d['B']:
    t = x['ocr']
    if len(t) < 2:
        continue
    if x.get('verdict', '').startswith(('窗口命中', '本集另有匹配', '全集库匹配')):
        continue
    if any(c in t for c in CREDIT):
        continue
    sus.append(x)
out = [f'剔除片尾职员表特征后剩余 {len(sus)} 条(需目视):']
for x in sorted(sus, key=lambda y: y['f']):
    out.append(f"  {x['f']:18s} wr={x['wr']:.3f} ocr=[{x['ocr']}] raw=[{(x['raw'] or '')[:50]}]"
               f" local={x.get('best_local')} all={x.get('best_all')}")
txt = '\n'.join(out)
open(os.path.join(B, 'review', 'orphan_suspect.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
