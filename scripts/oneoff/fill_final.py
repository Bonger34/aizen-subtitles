# -*- coding: utf-8 -*-
"""
fill_final.py — 收尾剩余真候选
- 17 条明确真对白: 扩大顺延(±20s)提取帧补录
- 其余 79 条(片尾名单/日文画面字): 写入各集 drop 清单
"""
import json
import os
import re
import sys

import cv2

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES = os.path.join(BASE, 'docs', 'frames')
CLEAN = os.path.join(BASE, 'subtitle_clean')
FMAP = os.path.join(BASE, 'docs', 'frames_map.js')
REVIEW = os.path.join(BASE, 'review')

# 明确真对白(集, 时间, 文本)
REAL = [
    ('P04', '0m09s', '秘密比如什么秘密啊'),
    ('P04', '0m24s', '那你来说说看啊'),
    ('P10', '9m58s', '好的'),
    ('P10', '11m13s', '活海哥'),
    ('P11', '7m19s', '爱染'),
    ('P11', '7m23s', '让市民入危险之中'),
    ('P20', '24m16s', '我们互相仇视对方'),
    ('P20', '24m17s', '根本不能解决问题'),
    ('P20', '24m23s', '那就让我来告诉你们'),
    ('P22', '4m50s', '你回来了'),
    ('P22', '24m08s', '下集也要收看哦'),
    ('P25', '23m26s', '你这次一定要回来啊'),
    ('P25', '23m32s', '好咧'),
    ('P25', '23m33s', '开工干活吧'),
    ('P25', '23m36s', '那我也走'),
    ('P25', '23m37s', '那我也走了'),
    ('P25', '23m52s', '就到此结束了'),
]


def ts_str(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def ts_sec(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2))


def main():
    # 1. 其余 79 条写入 drop 清单
    gap = json.load(open(os.path.join(REVIEW, 'gap_real.json'), encoding='utf-8'))
    real_keys = {(ep, ts, tx) for ep, ts, tx in REAL}
    for ep in sorted(gap.keys()):
        fixp = os.path.join(REVIEW, f'cont_fix_{ep}.json')
        fixd = json.load(open(fixp, encoding='utf-8')) if os.path.exists(fixp) else {'drop': [], 'fix': {}}
        added = 0
        for r in gap[ep]:
            if (ep, r['t'], r['text']) in real_keys:
                continue
            k = f'{r["t"]}:{r["text"]}'
            if k not in fixd['drop']:
                fixd['drop'].append(k)
                added += 1
        json.dump(fixd, open(fixp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        if added:
            print(f'{ep}: drop +{added}')

    # 2. 补录 17 条
    src = open(FMAP, encoding='utf-8').read()
    m = re.search(r'=\s*(\S.*)\s*;', src, re.S)
    fmap = json.loads(m.group(1))
    # 按集分组
    by_ep = {}
    for ep, ts, tx in REAL:
        by_ep.setdefault(ep, []).append((ts, tx))
    total = 0
    for ep, items in by_ep.items():
        f = [x for x in os.listdir(CLEAN) if x.startswith(f'[{ep}]') and x.endswith('.json')][0]
        path = os.path.join(CLEAN, f)
        arr = json.load(open(path, encoding='utf-8'))
        lib_ts = {e['timestamp'] for e in arr}
        used = set()
        for fn in os.listdir(FRAMES):
            mm = re.match(f'{re.escape(ep)}_(\\d+)m(\\d+)s\\.jpg$', fn)
            if mm:
                used.add(int(mm.group(1)) * 60 + int(mm.group(2)))
        # 从扫描数据取 fidx
        cont = json.load(open(os.path.join(REVIEW, f'cont_{ep}.json'), encoding='utf-8'))
        fps = cont['fps']
        cmap = {}
        for s in cont.get('seqs', []):
            cmap.setdefault((s['t'], s['text']), s['fidx'])
        picked = {}
        lib_texts = {e['text'] for e in arr}
        for ts, tx in items:
            if tx in lib_texts:      # 幂等: 已补录过则跳过
                print(f'  -- {ep} {ts} [{tx}] 已存在, 跳过')
                continue
            fidx = cmap.get((ts, tx))
            if fidx is None:
                print(f'  !! {ep} {ts} [{tx}] 无 fidx')
                continue
            base = round(fidx / fps)
            sec = None
            for delta in [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7, 8, -8,
                          9, -9, 10, -10, 12, -12, 15, -15, 20, -20]:
                cand = base + delta
                if cand >= 0 and ts_str(cand) not in lib_ts and cand not in used:
                    sec = cand
                    break
            if sec is None:
                print(f'  !! {ep} {ts} [{tx}] 无空闲秒')
                continue
            used.add(sec)
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
        print(f'{ep}: 补录 {len(got)} 条 (库 {len(arr)})')
    open(FMAP, 'w', encoding='utf-8').write('window.FRAMES_MAP = ' + json.dumps(fmap, ensure_ascii=False) + ';')
    print('合计补录', total, '映射键', len(fmap))


if __name__ == '__main__':
    main()
