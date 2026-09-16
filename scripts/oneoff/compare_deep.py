# -*- coding: utf-8 -*-
"""
compare_deep.py — 下探验证: 0.17s 扫描 vs 0.35s 密集扫描 vs 库
输出: 0.17s 有、0.35s 没有、库未覆盖的句 = 0.35s 仍漏的短句
用法: python compare_deep.py P01 [P13]
"""
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
           '商店街', 'スタッフ', '製作著作', '提供', '監督助手', '株式会社', '会社', '映像']
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
    return any(k in txt for k in SONG)


def overlap(a, b):
    if not a or not b:
        return 0
    return sum(1 for c in a if c in b) / len(a)


def main():
    eps = sys.argv[1:] or ['P01']
    for ep in eps:
        deep = json.load(open(os.path.join(REVIEW, f'deep_cont_{ep}.json'), encoding='utf-8'))
        dense = json.load(open(os.path.join(REVIEW, f'dense_cont_{ep}.json'), encoding='utf-8'))
        f = [x for x in os.listdir(CLEAN) if x.startswith(f'[{ep}]') and x.endswith('.json')][0]
        arr = json.load(open(os.path.join(CLEAN, f), encoding='utf-8'))
        lib = []
        for e in arr:
            m = re.match(r'(\d+)m(\d+)s', e['timestamp'])
            if m:
                lib.append((int(m.group(1)) * 60 + int(m.group(2)), norm(e['text'])))
        print(f'{ep}: 0.17s 区间 {deep["intervals"]} 采样 {deep["samples"]} | '
              f'0.35s 区间 {dense["intervals"]} 采样 {dense["samples"]}')
        print(f'    0.17s 唯一句 {len({s["text"] for s in deep.get("seqs", [])})}, '
              f'0.35s 唯一句 {len({s["text"] for s in dense.get("seqs", [])})}')
        dense_texts = [norm(s['text']) for s in dense.get('seqs', [])]
        new = []
        seen = set()
        for s in deep.get('seqs', []):
            tx = s['text']
            k = norm(tx)
            if k in seen or filtered(tx):
                continue
            seen.add(k)
            m = re.match(r'(\d+)m(\d+)s', s['t'])
            sec = int(m.group(1)) * 60 + int(m.group(2))
            win = [lt for ts, lt in lib if abs(ts - sec) <= 8]
            if win and max(overlap(k, w) for w in win) >= 0.6:
                continue
            if any(overlap(k, d) >= 0.6 for d in dense_texts):
                continue
            new.append((s['t'], tx))
        print(f'    0.17s 新发现(0.35s 未捕获且库未覆盖): {len(new)} 条')
        for t, tx in new[:30]:
            print(f'        {t} [{tx}]')


if __name__ == '__main__':
    main()
