# -*- coding: utf-8 -*-
"""
extract_cont_frames.py — 连续读帧提取候选全帧(960x540 jpg)
输入: review/cont_gap.json(未覆盖清单) + 排除规则(pass_filter)
输出: docs/frames/Pxx_XmXXs.jpg + review/cont_fill_{ep}.json(候选→帧映射)
用法: python extract_cont_frames.py P01 [P02 ...]
全程 cap.read() 顺序读(不 seek), 与扫描帧 fidx 100% 对齐
"""
import json
import os
import re
import sys

import cv2

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES = os.path.join(BASE, 'docs', 'frames')
GAP = os.path.join(BASE, 'review', 'cont_gap.json')
REVIEW = os.path.join(BASE, 'review')

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
    return re.sub(r'[，。！？、；：“”‘’\s]', '', s)


def pass_filter(txt):
    """True = 保留(真对白)"""
    if len(norm(txt)) < 2:
        return False
    if KANA.search(txt) or any(k in txt for k in CREDITS) or TITLE.search(txt):
        return False
    if any(k in txt for k in SONG):
        return False
    return True


def find_video(ep):
    for v in os.listdir(VIDEO_DIR):
        if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4'):
            return os.path.join(VIDEO_DIR, v)
    return None


def ts_str(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def main():
    eps = sys.argv[1:] or ['P01']
    gap = json.load(open(GAP, encoding='utf-8'))
    summary = {}
    for ep in eps:
        cont = json.load(open(os.path.join(REVIEW, f'cont_{ep}.json'), encoding='utf-8'))
        fps = cont['fps']
        # 候选: 从 gap 找 (t,text), 再从 seqs 找 fidx
        target = {}
        for r in gap.get(ep, []):
            if not pass_filter(r['text']):
                continue
            for s in cont.get('seqs', []):
                if s['text'] == r['text'] and s['t'] == r['t']:
                    target.setdefault(s['fidx'], r['text'])
                    break
        if not target:
            print(f'{ep}: 无候选', flush=True)
            continue
        # 已存在帧秒
        existing = set()
        for f in os.listdir(FRAMES):
            m = re.match(f'{re.escape(ep)}_(\\d+)m(\\d+)s\\.jpg$', f)
            if m:
                existing.add(int(m.group(1)) * 60 + int(m.group(2)))
        # 时间戳分配: 帧秒取整, 冲突顺延
        picked = {}
        used = set(existing)
        for fidx, text in sorted(target.items()):
            sec = round(fidx / fps)
            while sec in used:
                sec += 1
            used.add(sec)
            picked[fidx] = (sec, text)
        # 顺序读帧提全帧
        video = find_video(ep)
        cap = cv2.VideoCapture(video)
        got = {}
        fidx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if fidx in picked:
                sec, text = picked[fidx]
                small = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
                fname = f'{ep}_{ts_str(sec)}.jpg'
                cv2.imwrite(os.path.join(FRAMES, fname), small, [cv2.IMWRITE_JPEG_QUALITY, 90])
                got[sec] = {'text': text, 'frame': fname, 'fidx': fidx, 'ts': ts_str(sec)}
            fidx += 1
        cap.release()
        out = os.path.join(REVIEW, f'cont_fill_{ep}.json')
        json.dump(got, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        summary[ep] = len(got)
        print(f'{ep}: 提取 {len(got)} 帧 -> {out}', flush=True)
    print('完成:', summary, flush=True)


if __name__ == '__main__':
    main()
