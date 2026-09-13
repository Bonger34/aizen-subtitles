# -*- coding: utf-8 -*-
"""q_verifyall.py — 对"补扫仍未读到"的条目做帧图验证(带续跑与异常保护)。

为什么用帧图: 帧图是该条目的原始画面且已证实与库文本同源, 960x540 足以"证实旧文本";
而窗口补扫在 P01/P02 只证实了 22%, 却要 107 分钟。帧图方案 3 分钟可覆盖全部 1052 条。
用法: python q_verifyall.py [--limit N] [--eps P01,P02]
输出: review/q_verifyall.json (逐条写盘, 可中断续跑)
"""
import json
import os
import sys
import time

import cv2

from q_common import (SCAN_TOP, SCAN_BOT, build_engine, sim, split_lines)
from q_rescan import rec_pair, tight_x, MIN_SEG_FILL, MIN_SEG_H, MAX_SEGS

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
FR = os.path.join(B, 'Web', 'frames')
OUT = os.path.join(REVIEW, 'q_verifyall.json')
MAX_DENSITY = 0.60   # 帧图上亮背景会让整段白像素占比很高, 阈值放宽到 0.6
WHITE_MIN = 230      # 帧图用更严的白阈值, 否则"明亮天空"整片算白, 把字幕行一起吃进大段


def load_map():
    s = open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


def main():
    args = sys.argv[1:]
    limit = int(args[args.index('--limit') + 1]) if '--limit' in args else 0
    eps = set(args[args.index('--eps') + 1].split(',')) if '--eps' in args else None

    res = json.load(open(os.path.join(REVIEW, 'q_unmatched_resolved.json'), encoding='utf-8'))
    todo = res['unknown'] + res['no_reading']
    if eps:
        todo = [r for r in todo if r['ep'] in eps]
    if limit:
        todo = todo[:limit]
    done = {}
    if os.path.exists(OUT):
        for r in json.load(open(OUT, encoding='utf-8')).get('items', []):
            done[(r['ep'], r['ts'])] = r
    print(f'待验证 {len(todo)} 条 / 已完成 {len(done)} 条', flush=True)

    MAP = load_map()
    ocr = build_engine()
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    import numpy as np
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    paths = ('bin', 'raw')
    items = list(done.values())
    t0 = time.time()
    n_fail = 0
    for k, r in enumerate(todo, 1):
        if (r['ep'], r['ts']) in done:
            continue
        if k % 100 == 0:
            print(f'  {k}/{len(todo)} {time.time() - t0:.0f}s', flush=True)
        title = next(t for t in MAP if t.startswith(f"[{r['ep']}]")).split('|')[0]
        f = MAP.get(f"{title}|{r['ts']}")
        rec = {'ep': r['ep'], 'ts': r['ts'], 'old': r['old'], 'frame': f,
               'sim_old': 0.0, 'frame_text': '', 'segs': []}
        try:
            img = cv2.imread(os.path.join(FR, f)) if f else None
            if img is not None:
                segs = [s for s in split_lines(img, SCAN_TOP, SCAN_BOT,
                                               max_density=MAX_DENSITY, white_min=WHITE_MIN)
                        if s[1] - s[0] >= MIN_SEG_H and s[2] >= MIN_SEG_FILL]
                segs.sort(key=lambda s: -s[2])
                for y0, y1, fill in segs[:MAX_SEGS]:
                    tx = tight_x(img, y0, y1)
                    if not tx:
                        continue
                    rr = rec_pair(ocr, img, y0, y1, tx, paths)
                    rec['segs'].append(dict(rr, y0=y0, y1=y1, fill=fill))
        except Exception as e:
            rec['error'] = str(e)[:120]
            n_fail += 1
        cands = [(sim(s.get(p, ''), r['old']), s.get(p, ''))
                 for s in rec['segs'] for p in paths]
        if cands:
            rec['sim_old'], rec['frame_text'] = max(cands)
            rec['sim_old'] = round(rec['sim_old'], 3)
        items.append(rec)
        if k % 50 == 0:      # 逐段落盘, 便于中断续跑
            json.dump({'items': items}, open(OUT, 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
    json.dump({'items': items}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n_conf = sum(1 for r in items if r['sim_old'] >= 0.9)
    n_part = sum(1 for r in items if 0.55 <= r['sim_old'] < 0.9)
    n_no = sum(1 for r in items if r['sim_old'] < 0.55)
    print(f'完成 {len(items)} 条 / {time.time() - t0:.0f}s: 帧图证实旧文本 {n_conf} | '
          f'部分 {n_part} | 读不出 {n_no} | 异常 {n_fail}')
    print('输出:', OUT)


if __name__ == '__main__':
    main()
