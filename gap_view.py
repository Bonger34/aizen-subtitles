# -*- coding: utf-8 -*-
"""gap_view.py — 查看某集未覆盖清单(自动分歌词/中文), 带候选帧路径输出"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
EP = sys.argv[1] if len(sys.argv) > 1 else 'P01'
d = json.load(open(r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\review\cont_gap.json', encoding='utf-8'))
rows = d[EP]
kana = re.compile(r'[\u3040-\u30ff]')
# OP 歌词片段词(罗布 OP=超特急「超トキメキSentimental」逐句)
SONG = ['決', '絆', '諦', '繋', '未来', '君', '僕', '声', '乗', '越', '何百', '何千', '何万',
        '堅', '結', '手', '絶', '強', '羽', '物語', '瞬間', '奇', '跡', '嘘', '明日', '信',
        '抜', '輝', '愛', '情', '友', '交', '差', '帰', '場', '家', '族', '想', '忘', '誰',
        '壊', '銀', '河', '業', '振', '届', '星', '守', '光', '笑', '顔', '希', '望', '勇',
        '気', '全', '部', '重', '合', '行', '届', 'メ', 'キ', 'メ', 'セ', 'ン', 'ティ', 'め']
cn = []
song = 0
for r in rows:
    t = r['text']
    if kana.search(t) or any(s in t for s in SONG):
        song += 1
        continue
    cn.append(r)
print(f'{EP}: 歌词/日文 {song} 条, 中文候选 {len(cn)} 条')
# 同时读候选帧路径(从 cont_Pxx.json 的 cands 里按 t 匹配)
cont = json.load(open(rf'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\review\cont_{EP}.json', encoding='utf-8'))
framemap = {}
for c in cont['cands']:
    framemap.setdefault((c['t'], c['text']), c['frame'])
for r in cn:
    fp = framemap.get((r['t'], r['text']), '?')
    print(r['t'], r['text'], 'best=', r['best'], '|', fp.split('\\')[-1] if fp != '?' else fp)
