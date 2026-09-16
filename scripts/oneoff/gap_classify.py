# -*- coding: utf-8 -*-
"""gap_classify.py — 分类剩余未覆盖项: drop噪声 / 过滤噪声 / 真候选未回填"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
REVIEW = os.path.join(BASE, 'review')
gap = json.load(open(os.path.join(REVIEW, 'cont_gap.json'), encoding='utf-8'))

CREDITS = ['演技', '撮影', '監督', '音響', '美術', '製作', '制作', '演出', '協力', '応援',
           '企画', '監修', '主題歌', '作詞', '作曲', '選曲', '整音', '録音', '照明', '造形',
           '車両', '特技', '視覚', '特殊造形', '衣裳', '音楽', '番組', '背景', '編集', '円谷',
           '商店街', 'スタッフ', '製作著作', '提供', '監督助手']
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


stat = {'drop': 0, 'filtered': 0, 'real': 0}
reals = {}
for ep in sorted(gap.keys()):
    fixp = os.path.join(REVIEW, f'cont_fix_{ep}.json')
    fixd = json.load(open(fixp, encoding='utf-8')) if os.path.exists(fixp) else {'drop': []}
    for r in gap[ep]:
        if f'{r["t"]}:{r["text"]}' in fixd['drop']:
            stat['drop'] += 1
            continue
        if filtered(r['text']):
            stat['filtered'] += 1
            continue
        stat['real'] += 1
        reals.setdefault(ep, []).append(r)
print('分类:', stat)
print('真候选未回填按集:')
for ep in sorted(reals):
    print(' ', ep, len(reals[ep]))
    for r in reals[ep][:6]:
        print('     ', r['t'], r['text'], 'best=', r['best'])
json.dump(reals, open(os.path.join(REVIEW, 'gap_real.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
