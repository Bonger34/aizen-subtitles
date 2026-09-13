# -*- coding: utf-8 -*-
"""q_locate2_zoom.py — 把 q_locate2 定位到的原片帧字幕行放大导图, 用于逐字核对。

用法: python q_locate2_zoom.py P09:5m02s P24:3m29s ...
      python q_locate2_zoom.py --all-add          # 全部 add 候选
输出: review/loc2zoom/<EP>_<ts>.png (字幕行 2 倍放大)
"""
import json
import os
import re
import sys

import cv2

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
VIDEO_DIR = os.path.join(B, 'Videos')
OUT = os.path.join(REVIEW, 'loc2zoom')
PAD = 14


def load_rows(tag=''):
    rows = {}
    pat = re.compile(rf'q_locate2{tag}_P\d+\.json')
    for f in sorted(os.listdir(REVIEW)):
        if pat.fullmatch(f):
            for r in json.load(open(os.path.join(REVIEW, f), encoding='utf-8')):
                rows[(r['ep'], r['ts'])] = r
    return rows


def grab(ep, want):
    """顺序读一遍该集, 返回 {fno: frame}。"""
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    out, n, i, want = {}, 0, 0, sorted(want)
    while i < len(want):
        if not cap.grab():
            break
        if n == want[i]:
            ok, fr = cap.retrieve()
            if ok:
                out[n] = fr
            i += 1
        n += 1
    cap.release()
    return out


def main():
    args = sys.argv[1:]
    tag = ''
    if '--tag' in args:
        tag = args[args.index('--tag') + 1]
    rows = load_rows(tag)
    if '--all-add' in args:
        keys = [k for k, r in rows.items() if r['rel'] == 'add']
    else:
        keys = [(a.split(':')[0], a.split(':')[1]) for a in args if ':' in a]
    os.makedirs(OUT, exist_ok=True)
    by_ep = {}
    for ep, ts in keys:
        r = rows.get((ep, ts))
        if r and r['fno'] is not None:
            by_ep.setdefault(ep, []).append((ts, r))
    for ep, items in sorted(by_ep.items()):
        frames = grab(ep, [r['fno'] for _, r in items])
        for ts, r in items:
            fr = frames.get(r['fno'])
            if fr is None:
                print(f'  {ep} {ts}: 取帧失败')
                continue
            y0, y1 = (r['seg'] if r['seg'] else [880, 1000])
            y0, y1 = max(0, y0 - PAD), min(fr.shape[0], y1 + PAD)
            x0, x1 = 480, 1440
            c = fr[y0:y1, x0:x1]
            c = cv2.resize(c, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            p = os.path.join(OUT, f'{ep}_{ts}.png')
            cv2.imwrite(p, c)
            print(f'  {ep} {ts} y{y0}-{y1} -> {p}')
    print('输出目录:', OUT)


if __name__ == '__main__':
    main()
