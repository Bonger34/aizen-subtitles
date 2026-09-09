# -*- coding: utf-8 -*-
"""
compare_dense.py — 灵敏度检验对比: 密集扫描 vs 基线扫描 vs 库
输出: 密集扫描新发现(基线没有)且库未覆盖的句 = 疑似漏句
用法: python compare_dense.py P01
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


def overlap(a, b):
    if not a or not b:
        return 0
    return sum(1 for c in a if c in b) / len(a)


def main():
    ep = sys.argv[1] if len(sys.argv) > 1 else 'P01'
    dense = json.load(open(os.path.join(REVIEW, f'dense_cont_{ep}.json'), encoding='utf-8'))
    base = json.load(open(os.path.join(REVIEW, f'cont_{ep}.json'), encoding='utf-8'))
    # 库
    f = [x for x in os.listdir(CLEAN) if x.startswith(f'[{ep}]') and x.endswith('.json')][0]
    arr = json.load(open(os.path.join(CLEAN, f), encoding='utf-8'))
    lib = []
    for e in arr:
        m = re.match(r'(\d+)m(\d+)s', e['timestamp'])
        if m:
            lib.append((int(m.group(1)) * 60 + int(m.group(2)), norm(e['text'])))

    base_texts = {s['text'] for s in base.get('seqs', [])}
    print(f'{ep}: 密集区间 {dense["intervals"]} (基线 {base["intervals"]}), '
          f'密集采样 {dense["samples"]} (基线 {base["samples"]})')
    print(f'    密集唯一句 {len({s["text"] for s in dense.get("seqs", [])})}, '
          f'基线唯一句 {len({s["text"] for s in base.get("seqs", [])})}')

    # 密集扫描中: 库未覆盖 + 基线也没有的句
    new_sent = []
    seen = set()
    for s in dense.get('seqs', []):
        tx = s['text']
        k = norm(tx)
        if k in seen or filtered(tx):
            continue
        seen.add(k)
        m = re.match(r'(\d+)m(\d+)s', s['t'])
        sec = int(m.group(1)) * 60 + int(m.group(2))
        win = [lt for ts, lt in lib if abs(ts - sec) <= 8]
        if win:
            best = max(overlap(k, w) for w in win)
            if best >= 0.6:
                continue
        # 基线是否已有同句
        in_base = any(overlap(k, norm(b)) >= 0.6 for b in base_texts)
        if not in_base:
            new_sent.append((s['t'], tx, round(best if win else 0, 2)))

    print(f'\n密集扫描新发现(基线没有且库未覆盖): {len(new_sent)} 条')
    for t, tx, b in new_sent:
        print(f'  {t} [{tx}] best={b}')
    json.dump(new_sent, open(os.path.join(REVIEW, f'dense_new_{ep}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
