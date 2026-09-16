# -*- coding: utf-8 -*-
"""q_probe_frames.py — 把指定条目的帧裁剪带(y820~1080)拼成一张对照图, 供人工核对字幕布局。
用法: python q_probe_frames.py
输出: review/q_probe_*.jpg (带 ASCII 序号标签, 序号对应 review/q_probe_list.txt)
"""
import json
import os
import re

import cv2
import numpy as np

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'docs', 'frames')
CLEAN = os.path.join(B, 'subtitle_clean')

# 待查条目: (集号, 文本关键词)
TARGETS = [
    ('P18', '整坐城币得救'), ('P08', '件业田大筑关'), ('P21', '只万'), ('P21', '白千'),
    ('P01', '好烫店'), ('P01', '阿极'), ('P01', '绫香山'), ('P02', '電華'),
    ('P02', '技春'), ('P03', '城相公'), ('P03', '石鸟'), ('P02', '本度人'),
    # 对照: 正常条目
    ('P02', '勇海哥'), ('P05', ''),
]


def load_map():
    s = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
    return json.loads(re.search(r'=\s*(\{.*\})\s*;', s, re.S).group(1))


def main():
    MAP = load_map()
    files = {fn[:-5]: json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
             for fn in sorted(os.listdir(CLEAN)) if fn.endswith('.json')}
    tiles, listing = [], []
    for i, (ep, kw) in enumerate(TARGETS, 1):
        title = next(t for t in files if t.startswith(f'[{ep}]'))
        hit = None
        for e in files[title]:
            if kw and kw in e['text']:
                hit = e
                break
            if not kw and len(e['text']) >= 10 and 300 < int(re.match(r'(\d+)m', e['timestamp']).group(1)) * 60 < 1300:
                hit = e
                break
        if hit is None:
            listing.append(f'#{i} {title} [{kw}] 未找到')
            continue
        f = MAP.get(f'{title}|{hit["timestamp"]}')
        p = os.path.join(FR, f) if f else None
        listing.append(f'#{i} {title} {hit["timestamp"]} [{hit["text"]}] frame={f}')
        if not p or not os.path.exists(p):
            continue
        img = cv2.imread(p)
        h, w = img.shape[:2]
        # 取 y 820~1080(按 1080 比例) 的裁剪带, 放大到宽 1600
        y0, y1 = int(820 * h / 1080), min(h, int(1080 * h / 1080))
        band = img[y0:y1]
        band = cv2.resize(band, (1600, int(band.shape[0] * 1600 / band.shape[1])),
                          interpolation=cv2.INTER_CUBIC)
        cv2.putText(band, f'#{i}', (10, 46), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 4)
        tiles.append(band)
    if tiles:
        W = max(t.shape[1] for t in tiles)
        sheets, cur, hh = [], [], 0
        for t in tiles:
            if hh + t.shape[0] > 1500:
                sheets.append(np.vstack(cur))
                cur, hh = [], 0
            cur.append(t)
            hh += t.shape[0] + 4
        if cur:
            sheets.append(np.vstack(cur))
        for k, s in enumerate(sheets, 1):
            cv2.imwrite(os.path.join(B, 'review', f'q_probe_{k}.jpg'), s,
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
    txt = '\n'.join(listing)
    open(os.path.join(B, 'review', 'q_probe_list.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
