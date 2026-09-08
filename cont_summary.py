# -*- coding: utf-8 -*-
"""
cont_summary.py — 汇总 scan_cont 产出的全部候选
1. 按集读 review/cont_Pxx.json
2. 风格过滤(片尾名单/OP歌词/人名)
3. 与库 ±8s 二次匹配(重叠≥0.7 视为已覆盖)
4. 输出 review/cont_cands.json + 每集摘要(人工验证清单)
"""
import glob
import json
import os
import re

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(BASE, 'subtitle_clean')
REVIEW = os.path.join(BASE, 'review')

# 片尾名单/歌词关键模式(沿用 _tmp_filter22.py)
CREDITS = ['撮影', '監督', '音響', '美術', '製作', '制作', '演出', '協力', '応援', '助手',
           '企画', '監修', '主題歌', '作詞', '作曲', '編曲', '選曲', '整音', '録音', '照明',
           '造形', '車両', '特技', '視覚効果', '特殊造形', '演技事務', '制作主任', '装飾',
           '持道具', '衣裳', '音楽', '番組宣伝', '背景', '編集', '進行', '事務', '円谷',
           '監督助手', '手島', '島田', '岩田', '新井', '桑原', '横尾', '梶川', '永地',
           '丸田', '片岡', '武田', '山崎', '小林', '宮川', '花谷', '竹内', '佐木',
           '原規', '日比野', '菊地', '釜下', '山長', '徳田', '吉野', '嵯峨', '伊藤',
           '西野', '加村', '園田', '鎗水', '善史', '大城', '安藤', '佐藤', '倉田',
           '森谷', '三木', '岩村', '杉浦', '加藤', '山岡', '芦内', '島田知', '天州',
           '宍戸', '深沢', '土橋', '上田', '増田', '笹瀬', '山下', '大崎', '福富',
           '森美', '山長初', '村上', '関麻', '岩崎', '蓮田', '市川', '脇貴', '長井',
           '有村', '鎌田', '芳賀', '瓜生', '小柳', '田中', '辻岡', '植田', '小島',
           '開米', '橋本', '奥山', '原啓', '香川', '小原', '酒井', '小神野', '面川',
           '松居', '平木', '長谷川', '三好', '笹原', '加藤龍', '岡部', '石川',
           '美知', '出', '運', '羽', '稲', '期', '坂', '斎']
OP_LYRICS = ['決', '絆', '諦', '繋', '未来', '君笑', '君勇', '守全', '僕声', '重合',
             '乗越', '何百', '何千', '何万', '堅結', '手絶', '強羽', '物語', '瞬間',
             '起奇', '嘘', '明日', '信抜', '信先', '輝', '愛情', '友情', '交差', '帰場',
             '家族想', '忘決', '決誰', '壊', '誰誰愛', '見奇', '跡', '銀河', '業愛',
             '振河', '抜届', '星明日', '守抜']
# 特摄人名/称呼(罗布)
NAMES = ['罗索', '布鲁', '罗布', '爱染诚', '凑家', '凑勇海', '凑活海', '美剑', '达令',
         '爱染', '勇海', '活海', '凑渉', '凑朝阳', '朝阳', '佐久间', '石井', '真崎',
         '坂本', '東', '新', '音', '菱', 'ビスク', 'ソル', 'ウル', 'ゼロ', '大地', 'チヨ']


def norm(s):
    return re.sub(r'[，。！？、；：“”‘’\s]', '', s)


def overlap(a, b):
    if not a or not b:
        return 0
    return sum(1 for c in a if c in b) / len(a)


def style_filter(txt):
    ns = norm(txt)
    if len(ns) < 2:
        return False
    if any(k in txt for k in CREDITS):
        return False
    if any(k in txt for k in OP_LYRICS):
        return False
    return True


def main():
    lib_by_ep = {}
    for f in os.listdir(CLEAN):
        if f.endswith('.json'):
            ep = f[1:4]
            arr = json.load(open(os.path.join(CLEAN, f), encoding='utf-8'))
            lib_by_ep[ep] = []
            for e in arr:
                ts = e.get('timestamp') or ''
                m = re.match(r'(\d+)m(\d+)s', ts)
                if m:
                    lib_by_ep[ep].append((int(m.group(1)) * 60 + int(m.group(2)), norm(e.get('text') or '')))

    out = {}
    total_raw = total_style = total_final = 0
    for fp in sorted(glob.glob(os.path.join(REVIEW, 'cont_P*.json'))):
        ep = os.path.basename(fp)[5:8]
        d = json.load(open(fp, encoding='utf-8'))
        cands = d.get('cands', [])
        lib = lib_by_ep.get(ep, [])
        keep = []
        for c in cands:
            total_raw += 1
            txt = c.get('text', '')
            if not style_filter(txt):
                continue
            total_style += 1
            sec = int(c['t'][:-1].replace('m', ''))*60 if False else None
            m = re.match(r'(\d+)m(\d+)s', c['t'])
            sec = int(m.group(1)) * 60 + int(m.group(2))
            win = [lt for ts, lt in lib if abs(ts - sec) <= 8]
            if win:
                best = max(overlap(txt, w) for w in win)
                if best >= 0.7:
                    continue   # 已覆盖
                c['level'] = f'B(重叠{best:.2f})'
            else:
                c['level'] = 'A(窗口无句)'
            keep.append(c)
        out[ep] = keep
        total_final += len(keep)

    with open(os.path.join(REVIEW, 'cont_cands.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
    print(f'粗筛 {total_raw} → 样式过滤后 {total_style} → 最终候选 {total_final}')
    for ep, keep in sorted(out.items()):
        print(f'{ep}: {len(keep)}')
        for c in keep[:12]:
            print(f'  {c["t"]} [{c["text"]}] {c.get("level","")}')
    print('保存 review/cont_cands.json')


if __name__ == '__main__':
    main()
