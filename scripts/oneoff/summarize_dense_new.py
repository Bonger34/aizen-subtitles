# -*- coding: utf-8 -*-
"""
summarize_dense_new.py — 汇总密集扫描新发现, 过滤噪声, 输出真漏句清单
过滤: 假名/歌词/片尾名单/标题卡/短文本; 并排除"库中已有同义文本"(繁体变体等)
"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
REVIEW = os.path.join(BASE, 'review')
CLEAN = os.path.join(BASE, 'subtitle_clean')

CREDITS = ['演技', '撮影', '監督', '音響', '美術', '製作', '制作', '演出', '協力', '応援',
           '企画', '監修', '主題歌', '作詞', '作曲', '選曲', '整音', '録音', '照明', '造形',
           '車両', '特技', '視覚', '特殊造形', '衣裳', '音楽', '番組', '背景', '編集', '円谷',
           '商店街', 'スタッフ', '製作著作', '提供', '監督助手', '株式会社', '会社', '映像',
           '電通', '工務店', '公園', '県立', '拠点', '宣', '協会']
KANA = re.compile(r'[\u3040-\u30ff]')
TITLE = re.compile(r'第[0-9一二三四五六七八九十]+集')
SONG = ['決', '絆', '諦', '繋', '未来', '君', '僕', '声', '乗', '越', '何百', '何千', '何万',
        '堅', '結', '手', '絶', '強', '羽', '物語', '瞬間', '奇', '跡', '嘘', '明日', '信',
        '抜', '輝', '愛', '情', '友', '交', '差', '帰', '場', '家', '族', '想', '忘', '誰',
        '壊', '銀', '河', '業', '振', '届', '星', '守', '光', '笑', '顔', '希', '望', '勇',
        '気', '全', '部', '重', '合', '行']


def norm(s):
    return re.sub(r'[，。！？、；：“”‘’\s0-9]', '', s)


def filtered(txt):
    if len(norm(txt)) < 2:
        return True
    if KANA.search(txt) or any(k in txt for k in CREDITS) or TITLE.search(txt):
        return True
    if any(k in txt for k in SONG):
        return True
    return False


total_raw = 0
total_clean = 0
out = {}
for fp in sorted(glob.glob(os.path.join(REVIEW, 'dense_new_P*.json'))):
    ep = os.path.basename(fp)[10:13]
    rows = json.load(open(fp, encoding='utf-8'))
    total_raw += len(rows)
    # 库文本
    f = [x for x in os.listdir(CLEAN) if x.startswith(f'[{ep}]') and x.endswith('.json')][0]
    arr = json.load(open(os.path.join(CLEAN, f), encoding='utf-8'))
    lib_norm = [norm(e['text']) for e in arr]
    keep = []
    for t, tx, b in rows:
        if filtered(tx):
            continue
        n = norm(tx)
        # 库中已有近似文本(含繁体/顺序差异) -> 排除
        if any(n in ln or ln in n or
               (len(n) >= 2 and sum(1 for c in n if c in ln) / len(n) >= 0.75) for ln in lib_norm):
            continue
        keep.append({'t': t, 'text': tx, 'best': b})
    out[ep] = keep
    total_clean += len(keep)
    if keep:
        print(f'{ep}: 新发现 {len(rows)} -> 过滤后 {len(keep)}')
        for r in keep[:8]:
            print(f'    {r["t"]} [{r["text"]}]')
json.dump(out, open(os.path.join(REVIEW, 'dense_new_clean.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n合计: 原始 {total_raw} -> 真漏句候选 {total_clean}')
