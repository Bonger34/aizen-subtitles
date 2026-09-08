# -*- coding: utf-8 -*-
"""
fill_conflicts.py — 补录 cont_fill_all 因秒冲突跳过的候选
策略: 对重算后仍未覆盖的句(且不在 drop 清单), 找最近空闲秒(库无条目 & 帧文件不存在),
      顺序读帧提取全帧 -> 入库 -> 更新 frames_map
用法: python fill_conflicts.py [Pxx ...]
"""
import json
import os
import re
import sys

import cv2

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES = os.path.join(BASE, 'Web', 'frames')
CLEAN = os.path.join(BASE, 'subtitle_clean')
FMAP = os.path.join(BASE, 'Web', 'frames_map.js')
REVIEW = os.path.join(BASE, 'review')
GAP = os.path.join(REVIEW, 'cont_gap.json')

# 与 cont_fill_all 相同的过滤
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


def pass_filter(txt):
    if len(norm(txt)) < 2:
        return False
    if KANA.search(txt) or any(k in txt for k in CREDITS) or TITLE.search(txt):
        return False
    if any(k in txt for k in SONG):
        return False
    return True


def ts_str(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def main():
    eps = sys.argv[1:] or [f'P{i:02d}' for i in range(1, 26)]
    gap = json.load(open(GAP, encoding='utf-8'))
    src = open(FMAP, encoding='utf-8').read()
    total = 0
    for ep in eps:
        rows = gap.get(ep, [])
        fixp = os.path.join(REVIEW, f'cont_fix_{ep}.json')
        fixd = json.load(open(fixp, encoding='utf-8')) if os.path.exists(fixp) else {'drop': [], 'fix': {}}
        cont = json.load(open(os.path.join(REVIEW, f'cont_{ep}.json'), encoding='utf-8'))
        fps = cont['fps']
        cmap = {}
        for s in cont.get('seqs', []):
            cmap.setdefault((s['t'], s['text']), s['fidx'])
        # 库现有条目秒
        f = [x for x in os.listdir(CLEAN) if x.startswith(f'[{ep}]') and x.endswith('.json')][0]
        path = os.path.join(CLEAN, f)
        arr = json.load(open(path, encoding='utf-8'))
        lib_ts = {e['timestamp'] for e in arr}
        # 帧文件占用秒
        used = set()
        for fn in os.listdir(FRAMES):
            m = re.match(f'{re.escape(ep)}_(\\d+)m(\\d+)s\\.jpg$', fn)
            if m:
                used.add(int(m.group(1)) * 60 + int(m.group(2)))
        picked = {}
        for r in rows:
            key = (r['t'], r['text'])
            if f'{r["t"]}:{r["text"]}' in fixd['drop'] or not pass_filter(r['text']):
                continue
            if key not in cmap:
                continue
            fidx = cmap[key]
            base = round(fidx / fps)
            sec = base
            for delta in list(range(0, 5)) + list(range(-1, -5, -1)):
                cand = base + delta
                if cand not in used and ts_str(cand) not in lib_ts and cand >= 0:
                    sec = cand
                    break
            if ts_str(sec) in lib_ts or sec in used:
                print(f'  !! {ep} {r["t"]} [{r["text"]}] 无空闲秒', flush=True)
                continue
            used.add(sec)
            picked[fidx] = (sec, r['text'])
        if not picked:
            continue
        # 顺序读帧提取
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
        cap = cv2.VideoCapture(video)
        got = {}
        fidx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if fidx in picked:
                sec, text = picked[fidx]
                fname = f'{ep}_{ts_str(sec)}.jpg'
                small = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
                cv2.imwrite(os.path.join(FRAMES, fname), small, [cv2.IMWRITE_JPEG_QUALITY, 90])
                got[str(sec)] = {'text': text, 'frame': fname}
            fidx += 1
        cap.release()
        # 入库 + 映射
        for k in sorted(got.keys(), key=int):
            info = got[k]
            text = fixd['fix'].get(f'{info["frame"][4:-4]}:{info["text"]}', info['text'])
            arr.append({'timestamp': ts_str(int(k)), 'text': text, 'similarity': 0.0})
            title = f[:-5]
            entry = f'"{title}|{ts_str(int(k))}": "{info["frame"]}"'
            if src.rstrip().endswith('};'):
                src = src.rstrip()[:-1] + entry + '};'
            else:
                src = src.rstrip()[:-1] + ', ' + entry + '};'
        def tk(e):
            m = re.match(r'(\d+)m(\d+)s', e['timestamp'])
            return int(m.group(1)) * 60 + int(m.group(2)) if m else 0
        arr.sort(key=tk)
        json.dump(arr, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        total += len(got)
        print(f'{ep}: 补录 {len(got)} 条 (库 {len(arr)})', flush=True)
    open(FMAP, 'w', encoding='utf-8').write(src)
    print(f'合计补录 {total} 条', flush=True)


if __name__ == '__main__':
    main()
