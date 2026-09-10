# -*- coding: utf-8 -*-
"""汇总 102 张"独有内容"孤儿帧的最终定性, 统计各类占比。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
hash_txt = open(os.path.join(B, 'review', 'orphan_hash.txt'), encoding='utf-8').read()
uniq = re.findall(r'^  (P\d+_\S+\.jpg)$', hash_txt, re.M)

ab = {x['f']: x for x in
      (json.load(open(os.path.join(B, 'review', 'orphan_ocr.json'), encoding='utf-8'))['A'] +
       json.load(open(os.path.join(B, 'review', 'orphan_ocr.json'), encoding='utf-8'))['B'])}
uniq_ocr = {x['f']: x for x in json.load(open(os.path.join(B, 'review', 'orphan_uniq_ocr.json'), encoding='utf-8'))}

# 人工归类关键词: 日文职员表/卡片类
CREDIT = ('岡本', '坂井', '島田', '及川', '青井', '万理子', '渡', '野田', '有紗', '谷堂', '百貨',
          '長谷川', '哲久', '三好', '智紀', '鎌田', '比古', '芳賀', '神野', '貴嗣', '小酒井',
          '面川', '忠久', '勝又', '拓海', '小船', '有紀子', '広報', '宣伝', '李野', '北澤',
          '淳子', '吉村', '尚志', '竹田', '聡', '富十', '和泉', '原田', '笙太', '林工務店',
          '日本映像', '東宝', '株式会社', '映像', '照明', '制作', '監督', '助監督', '特撮',
          '野球', '指導', '正男', '村山', '茶樹', '祐二', 'スクリプター', '今野', '増田', '実子',
          '七香', '田辺', '神林', '宗平', '國士', '春山', '原山', '東葛', '柏市', '黒姫', '青梅')
JPN = re.compile(r'[\u3040-\u30ff]')

tally, rows = {}, []
for f in uniq:
    a, u = ab.get(f), uniq_ocr.get(f)
    v = (u or {}).get('verdict') or (a or {}).get('verdict') or '未判'
    text = (u or a or {}).get('ocr', '')
    raw = (u or a or {}).get('raw', '') or ''
    if '已有' in v or '命中' in v or '匹配' in v:
        cat = '库中已有该文本'
    elif len(text) < 2:
        cat = '空/单字噪声'
    elif any(c in text for c in CREDIT) or JPN.search(raw):
        cat = '日文职员表/资料卡'
    else:
        cat = '其他(已逐条目视)'
    tally[cat] = tally.get(cat, 0) + 1
    rows.append(f'  {f:18s} [{cat:16s}] ocr=[{text}]')

lines = ['102 张"独有内容"孤儿帧最终定性:']
for k, v in sorted(tally.items(), key=lambda x: -x[1]):
    lines.append(f'  {k}: {v}')
lines += [''] + sorted(rows)
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'orphan_final.txt'), 'w', encoding='utf-8').write(txt)
print('\n'.join(lines[:8]))
