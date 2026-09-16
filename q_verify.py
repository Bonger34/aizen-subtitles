# -*- coding: utf-8 -*-
"""q_verify.py — 帧图第三方验证: 用搜索界面实际显示的帧图(960x540)对判定存疑的条目做独立识别。

用途: q_align_tl 判为 review(含删除/替换, 方向不可自动判定)或 unmatched(时间线未读到)的条目,
再用帧图读一遍 —— 帧图与库文本同源(抽帧时经 OCR 校验), 但裁剪与分辨率独立, 因此构成第三票:
  * 帧图同样支持旧文本 -> 保留;
  * 帧图支持时间线的新文本 -> 采用;
  * 两边都不明确 -> 转人工。
用法: python q_verify.py [review|unmatched|all] [--eps P01,P02] [--limit N]
输出: review/q_verify_<类型>.json
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
FR = os.path.join(B, 'docs', 'frames')
MAX_DENSITY = 0.45      # 丢弃"整片白"的段(画面亮部), 见 q_common.split_lines 注释


def load_map():
    s = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


def main():
    args = sys.argv[1:]
    want = args[0] if args and not args[0].startswith('-') else 'review'
    eps = None
    if '--eps' in args:
        eps = set(args[args.index('--eps') + 1].split(','))
    limit = int(args[args.index('--limit') + 1]) if '--limit' in args else 0

    d = json.load(open(os.path.join(REVIEW, 'q_align_tl.json'), encoding='utf-8'))
    MAP = load_map()
    todo = []
    for ep in sorted(d):
        if eps and ep not in eps:
            continue
        title = next(t for t in MAP if t.startswith(f'[{ep}]')).split('|')[0]
        for i, r in enumerate(d[ep]['items']):
            if want != 'all' and r['verdict'] != want:
                continue
            todo.append((ep, title, i, r))
    if limit:
        todo = todo[:limit]
    print(f'待验证 {len(todo)} 条 ({want})', flush=True)

    ocr = build_engine()
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    import numpy as np
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    paths = ('bin', 'raw')
    out, t0, t_ocr = [], time.time(), 0.0
    n_seg_fail = 0
    for k, (ep, title, i, r) in enumerate(todo):
        if k % 300 == 0:
            print(f'  {k}/{len(todo)} {time.time() - t0:.0f}s', flush=True)
        f = MAP.get(f'{title}|{r["ts"]}')
        img = cv2.imread(os.path.join(FR, f)) if f else None
        rec = {'ep': ep, 'idx': i, 'ts': r['ts'], 'old': r['old'],
               'verdict0': r['verdict'], 'new_tl': r.get('new'), 'sim_tl': r.get('best_sim'),
               'kind': r.get('kind'), 'frame': f, 'segs': []}
        if img is None:
            out.append(rec)
            continue
        segs = [s for s in split_lines(img, SCAN_TOP, SCAN_BOT, max_density=MAX_DENSITY)
                if s[1] - s[0] >= MIN_SEG_H and s[2] >= MIN_SEG_FILL]
        segs.sort(key=lambda s: -s[2])
        if not segs:
            n_seg_fail += 1
        for y0, y1, fill in segs[:MAX_SEGS]:
            tx = tight_x(img, y0, y1)
            if not tx:
                continue
            ta = time.time()
            rr = rec_pair(ocr, img, y0, y1, tx, paths)
            t_ocr += time.time() - ta
            rec['segs'].append(dict(rr, y0=y0, y1=y1, fill=fill, x0=tx[0], x1=tx[1]))
        # 先定位"与旧文本最相似的段读数"(即字幕所在那一段), 再在同一读数上比新文本 ——
        # 若两处分别取最大值, 会拿画面里另一处无关文字去"支持"新文本(实测踩过)。
        cands = [(sim(s.get(p, ''), r['old']), s.get(p, ''))
                 for s in rec['segs'] for p in paths]
        best_old, frame_text = max(cands) if cands else (0.0, '')
        rec['sim_frame_old'] = round(best_old, 3)
        rec['frame_text'] = frame_text
        rec['sim_frame_new'] = (round(sim(frame_text, r['new']), 3)
                                if r.get('new') else 0.0)
        out.append(rec)
    el = time.time() - t0
    res = {'want': want, 'n': len(out), 'n_seg_fail': n_seg_fail, 'elapsed': round(el, 1),
           'elapsed_ocr': round(t_ocr, 1), 'items': out}
    p = os.path.join(REVIEW, f'q_verify_{want}.json')
    json.dump(res, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n_sup_old = sum(1 for r in out if r['sim_frame_old'] >= 0.9)
    n_sup_new = sum(1 for r in out if r.get('sim_frame_new', 0) >= 0.9 > r['sim_frame_old'])
    print(f'完成 {len(out)} 条 / {el:.0f}s: 帧图支持旧文本 {n_sup_old} | '
          f'支持新文本 {n_sup_new} | 段切分失败 {n_seg_fail}')
    print('输出:', p)


if __name__ == '__main__':
    main()
