# -*- coding: utf-8 -*-
"""q_webcheck.py — 用"搜索界面实际显示的帧图(docs/frames, 960x540)"重读字幕。

动机: 用户搜索时看到的就是这张图, 文本必须与这张图一致。而 q_rescan 从视频按库时间戳取帧,
实测大量条目取到的却是相邻句 —— 说明"库时间戳"与"帧图"未必同步。于是改为直接读帧图本身:
  * 帧图只有一张, 不存在取帧位置问题; 判定时用 sim(新文本, 旧文本) 识别"帧文错配"的条目。
用法: python q_webcheck.py P01 P02 ...
输出: review/q_web_<EP>.json
"""
import json
import os
import sys
import time

import cv2

from q_common import (SCAN_TOP, SCAN_BOT, X0, X1, PAD_Y, build_engine, crop_norm,
                      gray_white, sim, split_lines)
from q_rescan import rec_pair, tight_x, MIN_SEG_FILL, MIN_SEG_H, MAX_SEGS

B = os.path.dirname(os.path.abspath(__file__))
FR = os.path.join(B, 'docs', 'frames')
CLEAN = os.path.join(B, 'subtitle_clean')
OUT_DIR = os.path.join(B, 'review')


def load_map():
    s = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


def check_ep(ocr, ep, paths=('bin', 'raw')):
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]
    title = fn[:-5]
    data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
    MAP = load_map()
    items, t_ocr, n_rec = [], 0.0, 0
    t0 = time.time()
    for i, e in enumerate(data):
        ts, old = e.get('timestamp'), e.get('text', '')
        f = MAP.get(f'{title}|{ts}')
        p = os.path.join(FR, f) if f else None
        if not f or not os.path.exists(p):
            items.append({'ts': ts, 'old': old, 'frame': None, 'segs': [], 'best': 0.0})
            continue
        img = cv2.imread(p)
        if img is None:
            items.append({'ts': ts, 'old': old, 'frame': f, 'segs': [], 'best': 0.0})
            continue
        segs = [s for s in split_lines(img, SCAN_TOP, SCAN_BOT)
                if s[1] - s[0] >= MIN_SEG_H and s[2] >= MIN_SEG_FILL]
        segs.sort(key=lambda s: -s[2])
        recs = []
        for y0, y1, fill in segs[:MAX_SEGS]:
            tx = tight_x(img, y0, y1)
            if not tx:
                continue
            ta = time.time()
            r = rec_pair(ocr, img, y0, y1, tx, paths)
            t_ocr += time.time() - ta
            n_rec += len(paths)
            recs.append(dict(r, y0=y0, y1=y1, fill=fill, x0=tx[0], x1=tx[1],
                             sim_old=round(max(sim(r.get(pp, ''), old) for pp in paths), 3)))
        best = max([r['sim_old'] for r in recs] or [0.0])
        items.append({'ts': ts, 'old': old, 'frame': f, 'segs': recs, 'best': best})
    el = time.time() - t0
    out = {'ep': ep, 'title': title, 'paths': list(paths), 'n_entries': len(data),
           'n_rec': n_rec, 'elapsed': round(el, 1), 'elapsed_ocr': round(t_ocr, 1),
           'items': items}
    json.dump(out, open(os.path.join(OUT_DIR, f'q_web_{ep}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    n_hit = sum(1 for it in items if it['best'] >= 0.95)
    n_mid = sum(1 for it in items if 0.6 <= it['best'] < 0.95)
    n_low = sum(1 for it in items if it['best'] < 0.6)
    print(f'{ep}: {len(data)} 条 / rec {n_rec} 次 / {el:.1f}s(OCR {t_ocr:.1f}s) '
          f'| 帧文一致 {n_hit} / 部分 {n_mid} / 不一致 {n_low}', flush=True)
    return out


def main():
    eps = [a for a in sys.argv[1:] if not a.startswith('-')] or ['P01']
    ocr = build_engine()
    import numpy as np
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    print('RapidOCR rec-only 就绪(帧图模式)', flush=True)
    for ep in eps:
        check_ep(ocr, ep)


if __name__ == '__main__':
    main()
