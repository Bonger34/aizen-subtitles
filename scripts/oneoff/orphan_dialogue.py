# -*- coding: utf-8 -*-
"""重筛: 不看判定结果, 先剔除日文职员表特征, 列出所有含"对话样文本"的孤儿帧及其匹配去向。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
d = json.load(open(os.path.join(B, 'review', 'orphan_ocr.json'), encoding='utf-8'))

libs = {}
for fn in os.listdir(CLEAN):
    m = re.match(r'\[(P\d+)\]', fn)
    if not m:
        continue
    rows = []
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        mm = re.match(r'(\d+)m(\d+)s', e.get('timestamp') or '')
        t = ''.join(re.findall(r'[\u4e00-\u9fff]', e.get('text') or ''))
        if mm and t:
            rows.append((int(mm.group(1)) * 60 + int(mm.group(2)), t))
    libs[m.group(1)] = rows
allrows = [(ep,) + r for ep, rows in libs.items() for r in rows]

CREDIT = ('岡本', '坂井', '島田', '及川', '青井', '万理子', '渡', '野田', '有紗', '谷堂', '百貨',
          '長谷川', '哲久', '三好', '智紀', '鎌田', '比古', '芳賀', '神野', '貴嗣', '小酒井',
          '面川', '忠久', '勝又', '拓海', '小船', '有紀子', '広報', '宣伝', '李野', '北澤',
          '淳子', '吉村', '尚志', '竹田', '聡', '富十', '和泉', '原田', '笙太', '林工務店',
          '日本映像', '東宝', '株式会社', '映像', '照明', '制作', '監督', '助監督', '特撮',
          '野球', '指導', '正男', '村山', '茶樹', '祐二', 'ドローン', 'スクリプター', '今野',
          '増田', '実子', '七香', '田辺', '神林', '宗平', '國士', '春山', 'ゆきお', '原山')


def bef(tn, w):
    return sum(1 for c in tn if c in w) / len(tn) if tn and w else 0.0


rows = []
for tag in ('A', 'B'):
    for x in d[tag]:
        t = x['ocr']
        if len(t) < 2:
            continue
        if any(c in t for c in CREDIT):
            continue
        ep = x['f'][:3]
        # 找出最匹配的库条目及偏移
        top, arg = 0.0, None
        for r in allrows:
            s = bef(t, r[2])
            if s > top:
                top, arg = s, r
        rows.append((x, tag, top, arg))

out = [f'非职员表类孤儿帧 {len(rows)} 条(A/B 合计, 含已命中):']
for x, tag, top, arg in sorted(rows, key=lambda y: y[0]['f']):
    loc = f'{arg[0]} {arg[1]//60}m{arg[1]%60:02d}s [{arg[2]}]' if arg else '-'
    out.append(f"  [{tag}] {x['f']:18s} wr={x['wr']:.3f} ocr=[{x['ocr']}] "
               f"best={top:.2f} -> {loc}")
txt = '\n'.join(out)
open(os.path.join(B, 'review', 'orphan_dialogue.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
