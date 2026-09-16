# -*- coding: utf-8 -*-
"""现有孤儿帧(102 张独有内容)的逐张问答: 画面里有没有台词字幕? 该台词在不在库里?

对每张:
  1. 用已 OCR 的字幕带文本判断类型(中文台词 / 日文职员表·资料卡 / 空或单字);
  2. 中文台词类: 与【当前】字幕库全库匹配(包含度 >=0.6 视为库中已有), 输出对应条目。
"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'docs', 'frames')
CLEAN = os.path.join(B, 'subtitle_clean')

MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                           open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read(),
                           re.S).group(1))
ref = {v for v in MAP.values() if isinstance(v, str)}
orphans = sorted(set(os.listdir(FR)) - ref)
print('当前孤儿帧:', len(orphans))

OCR = {}
for src, key in (('orphan_ocr.json', None), ('orphan_uniq_ocr.json', None)):
    d = json.load(open(os.path.join(B, 'review', src), encoding='utf-8'))
    if isinstance(d, dict):
        for tag in ('A', 'B'):
            for x in d.get(tag, []):
                OCR[x['f']] = x
    else:
        for x in d:
            OCR[x['f']] = x

lib = collections.defaultdict(list)
for fn in os.listdir(CLEAN):
    m = re.match(r'\[(P\d+)\]', fn)
    if not m:
        continue
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        t = ''.join(re.findall(r'[\u4e00-\u9fff]', e.get('text') or ''))
        if t:
            lib[m.group(1)].append((e['timestamp'], t))
allrows = [(ep,) + r for ep, rows in lib.items() for r in rows]

CREDIT = ('岡本', '坂井', '島田', '及川', '青井', '万理子', '渡', '野田', '有紗', '谷堂', '百貨',
          '長谷川', '哲久', '三好', '智紀', '鎌田', '比古', '芳賀', '神野', '貴嗣', '小酒井',
          '面川', '忠久', '勝又', '拓海', '小船', '有紀子', '広報', '宣伝', '李野', '北澤',
          '淳子', '吉村', '尚志', '竹田', '聡', '富十', '和泉', '原田', '笙太', '林工務店',
          '日本映像', '東宝', '株式会社', '映像', '照明', '制作', '監督', '助監督', '特撮',
          '野球', '指導', '正男', '村山', '茶樹', '祐二', 'スクリプター', '今野', '増田', '実子',
          '七香', '田辺', '神林', '宗平', '國士', '春山', '原山', '東葛', '柏市', '黒姫', '青梅')
JPN = re.compile(r'[\u3040-\u30ff]')


def bef(tn, w):
    return sum(1 for c in tn if c in w) / len(tn) if tn and w else 0.0


cnt = collections.Counter()
rows = []
for f in orphans:
    x = OCR.get(f)
    text = (x or {}).get('ocr', '')
    raw = (x or {}).get('raw', '') or ''
    # 先查库匹配(字幕与职员表叠加的帧也能识别出中文台词), 再退回"是否日文文本"
    top, arg = 0.0, None
    if len(text) >= 2:
        for r in allrows:
            s = bef(text, r[2])
            if s > top:
                top, arg = s, r
    hit = arg if top >= 0.6 else None
    if hit:
        cat = '有中文字幕·库中已有该句'
    elif len(text) < 2:
        cat = '无中文字幕(白屏/误检)'
    elif any(c in text for c in CREDIT) or JPN.search(raw):
        cat = '无中文字幕(日文职员表或资料卡)'
    else:
        cat = '有中文字幕·待判'
    cnt[cat] += 1
    rows.append((f, cat, text, top, hit, (x or {}).get('wr')))

lines = ['剩余 102 张孤儿帧问答: 画面里有没有台词字幕?', '']
for k, v in cnt.most_common():
    lines.append(f'  {k}: {v}')
lines.append('')
for f, cat, text, best, hit, wr in sorted(rows, key=lambda r: (r[1], r[0])):
    loc = f'{hit[0]} {hit[1]} [{hit[2][:16]}]' if hit else '-'
    lines.append(f'  {f:18s} wr={wr if wr is None else round(wr, 3)} [{cat}] ocr=[{text}] -> {loc}')
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'orphan_102_answer.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
