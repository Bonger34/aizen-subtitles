# -*- coding: utf-8 -*-
"""
fill_dense.py — 回填密集扫描发现的短句(短句漏句补全)
输入: review/dense_fill_list.json  {集: [[ts, text], ...]}
       review/dense_cont_{ep}.json  (seqs 提供 fidx)
流程: 秒分配(冲突顺延) -> 顺序读帧提全帧 -> 入库 + frames_map -> 重建映射
"""
import json
import os
import re
import sys

import cv2

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES = os.path.join(BASE, 'Web', 'frames')
CLEAN = os.path.join(BASE, 'subtitle_clean')
FMAP = os.path.join(BASE, 'Web', 'frames_map.js')
REVIEW = os.path.join(BASE, 'review')


def ts_str(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def ts_sec(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2))


def main():
    lst = json.load(open(os.path.join(REVIEW, 'dense_fill_list.json'), encoding='utf-8'))
    fmap = json.loads(re.search(r'=\s*(\S.*)\s*;', open(FMAP, encoding='utf-8').read(), re.S).group(1))
    total = 0
    for ep in sorted(lst.keys()):
        items = lst[ep]
        dense = json.load(open(os.path.join(REVIEW, f'dense_cont_{ep}.json'), encoding='utf-8'))
        fps = dense['fps']
        # (ts, text) -> fidx
        cmap = {}
        for s in dense.get('seqs', []):
            cmap.setdefault((s['t'], s['text']), s['fidx'])
        f = [x for x in os.listdir(CLEAN) if x.startswith(f'[{ep}]') and x.endswith('.json')][0]
        path = os.path.join(CLEAN, f)
        arr = json.load(open(path, encoding='utf-8'))
        lib_ts = {e['timestamp'] for e in arr}
        lib_texts = {e['text'] for e in arr}
        used = set()
        for fn in os.listdir(FRAMES):
            m = re.match(f'{re.escape(ep)}_(\\d+)m(\\d+)s\\.jpg$', fn)
            if m:
                used.add(int(m.group(1)) * 60 + int(m.group(2)))
        picked = {}
        for ts, tx in items:
            if tx in lib_texts:
                print(f'  -- {ep} {ts} [{tx}] 库已有, 跳过')
                continue
            fidx = cmap.get((ts, tx))
            if fidx is None:
                print(f'  !! {ep} {ts} [{tx}] 无 fidx')
                continue
            base = round(fidx / fps)
            sec = None
            for delta in [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 8, -8, 10, -10]:
                cand = base + delta
                if cand >= 0 and ts_str(cand) not in lib_ts and cand not in used:
                    sec = cand
                    break
            if sec is None:
                print(f'  !! {ep} {ts} [{tx}] 无空闲秒')
                continue
            used.add(sec)
            lib_ts.add(ts_str(sec))
            picked[fidx] = (sec, tx)
        if not picked:
            continue
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
        cap = cv2.VideoCapture(video)
        fidx = 0
        got = {}
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if fidx in picked:
                sec, tx = picked[fidx]
                fname = f'{ep}_{ts_str(sec)}.jpg'
                small = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
                cv2.imwrite(os.path.join(FRAMES, fname), small, [cv2.IMWRITE_JPEG_QUALITY, 90])
                got[sec] = (fname, tx)
            fidx += 1
        cap.release()
        title = f[:-5]
        for sec in sorted(got):
            fname, tx = got[sec]
            arr.append({'timestamp': ts_str(sec), 'text': tx, 'similarity': 0.0})
            fmap[f'{title}|{ts_str(sec)}'] = fname
        arr.sort(key=lambda e: ts_sec(e['timestamp']))
        json.dump(arr, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        total += len(got)
        print(f'{ep}: 回填 {len(got)} 条 (库 {len(arr)})')
    # 重建映射(以库为基准)
    new = {}
    for fn in sorted(os.listdir(CLEAN)):
        if not fn.endswith('.json'):
            continue
        title = fn[:-5]
        ep2 = fn[1:4]
        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
            key = f'{title}|{e["timestamp"]}'
            fname = fmap.get(key)
            if fname and os.path.exists(os.path.join(FRAMES, fname)):
                new[key] = fname
            elif os.path.exists(os.path.join(FRAMES, f'{ep2}_{e["timestamp"]}.jpg')):
                new[key] = f'{ep2}_{e["timestamp"]}.jpg'
            else:
                print('缺帧', key)
    open(FMAP, 'w', encoding='utf-8').write('window.FRAMES_MAP = ' + json.dumps(new, ensure_ascii=False) + ';')
    print(f'合计回填 {total} 条, 映射键 {len(new)}')


if __name__ == '__main__':
    main()
