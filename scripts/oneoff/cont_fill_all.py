# -*- coding: utf-8 -*-
"""
cont_fill_all.py — 通用回填: 从 cont_gap.json 提取候选全帧 + 更新库与 frames_map
用法: python cont_fill_all.py P01 [P02 ...]   (缺省处理全部已有 gap 的集)
人工修正/排除: 每集可选 data/review/cont_fix_{ep}.json
  {"drop": ["2m08s:不过这衣服是不是有点太花哨了啊", ...], "fix": {"2m08s:旧文本": "新文本"}}
流程: 过滤(=extract 规则) -> 帧提取(连续读) -> 库追加(冲突顺延已由帧名承载, 此处只查 ts 存在) -> frames_map 增量
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
CLEAN = os.path.join(BASE, 'subtitle_clean')
FMAP = os.path.join(BASE, 'docs', 'frames_map.js')

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


def find_video(ep):
    for v in os.listdir(VIDEO_DIR):
        if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4'):
            return os.path.join(VIDEO_DIR, v)
    return None


def ts_str(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def load_fix(ep):
    fp = os.path.join(REVIEW, f'cont_fix_{ep}.json')
    if os.path.exists(fp):
        return json.load(open(fp, encoding='utf-8'))
    return {'drop': [], 'fix': {}}


def main():
    eps = sys.argv[1:] or []
    gap = json.load(open(GAP, encoding='utf-8'))
    if not eps:
        eps = sorted(gap.keys())
    src = open(FMAP, encoding='utf-8').read()
    total_new = 0
    for ep in eps:
        if ep not in gap:
            continue
        cont = json.load(open(os.path.join(REVIEW, f'cont_{ep}.json'), encoding='utf-8'))
        fps = cont['fps']
        fixd = load_fix(ep)
        cmap = {}
        for s in cont.get('seqs', []):
            cmap.setdefault((s['t'], s['text']), s['fidx'])
        # 候选 (fidx, text)
        target = {}
        for r in gap[ep]:
            if not pass_filter(r['text']):
                continue
            key = (r['t'], r['text'])
            if f'{r["t"]}:{r["text"]}' in fixd['drop']:
                continue
            if key in cmap:
                target.setdefault(cmap[key], r['text'])
        if not target:
            print(f'{ep}: 无候选', flush=True)
            continue
        # 帧秒分配
        existing = set()
        for f in os.listdir(FRAMES):
            m = re.match(f'{re.escape(ep)}_(\\d+)m(\\d+)s\\.jpg$', f)
            if m:
                existing.add(int(m.group(1)) * 60 + int(m.group(2)))
        used = set(existing)
        picked = {}   # fidx -> (sec, text)
        for fidx, text in sorted(target.items()):
            sec = round(fidx / fps)
            while sec in used:
                sec += 1
            used.add(sec)
            picked[fidx] = (sec, text)
        # 提取
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
                fname = f'{ep}_{ts_str(sec)}.jpg'
                small = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
                cv2.imwrite(os.path.join(FRAMES, fname), small, [cv2.IMWRITE_JPEG_QUALITY, 90])
                got[str(sec)] = {'text': text, 'frame': fname, 'fidx': fidx, 'ts': ts_str(sec)}
            fidx += 1
        cap.release()
        # 库追加
        f = [x for x in os.listdir(CLEAN) if x.startswith(f'[{ep}]') and x.endswith('.json')][0]
        path = os.path.join(CLEAN, f)
        arr = json.load(open(path, encoding='utf-8'))
        exist_ts = {e['timestamp'] for e in arr}
        to_add = []
        for k in sorted(got.keys(), key=int):
            info = got[k]
            if info['ts'] in exist_ts:
                print(f'  !! {ep} 秒冲突 {info["ts"]} [{info["text"]}] 跳过', flush=True)
                continue
            text = fixd['fix'].get(f'{info["ts"]}:{info["text"]}', info['text'])
            arr.append({'timestamp': info['ts'], 'text': text, 'similarity': 0.0})
            to_add.append(info)
        def tk(e):
            m = re.match(r'(\d+)m(\d+)s', e['timestamp'])
            return int(m.group(1)) * 60 + int(m.group(2)) if m else 0
        arr.sort(key=tk)
        json.dump(arr, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        # frames_map 增量
        title = f[:-5]
        for info in to_add:
            key = f'"{title}|{info["ts"]}": "{info["frame"]}"'
            if key[1:-1].split(':')[0].strip() not in src:
                if src.rstrip().endswith('};'):
                    src = src.rstrip()[:-1] + f'"{title}|{info["ts"]}": "{info["frame"]}"' + '};'
                else:
                    src = src.rstrip()[:-1] + f', "{title}|{info["ts"]}": "{info["frame"]}"' + '};'
        open(FMAP, 'w', encoding='utf-8').write(src)
        total_new += len(to_add)
        print(f'{ep}: 回填 {len(to_add)} 条 (库 {len(arr)})', flush=True)
        json.dump(got, open(os.path.join(REVIEW, f'cont_fill_{ep}.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    print(f'全部完成, 新增 {total_new} 条', flush=True)


if __name__ == '__main__':
    main()
