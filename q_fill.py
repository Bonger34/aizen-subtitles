# -*- coding: utf-8 -*-
"""q_fill.py — 对"时间线无读数"的条目做窗口补扫: 只在这些条目的时间窗内加密采样。

为什么需要: q_timeline 全片按 0.25s 采样且 MIN_GAP=0.5s, 实测有 1052 条台词在这套参数下
一次都没被读到(窗口内根本没有可用读数)。这些条目时间戳与视频的漂移在 -3.2s~+1.1s 内,
所以取 ±3.5s 窗口、0.167s 采样、MIN_GAP 降到 0.167s, 只扫这些窗口, 成本远低于全片重扫。

用法: python q_fill.py [--step 4] [--half 3.5] [P01 P02 ...]
输出: review/q_fill_<EP>.json
"""
import json
import os
import sys
import time

import cv2
import numpy as np

from q_common import (SCAN_TOP, SCAN_BOT, build_engine, split_lines)
from q_rescan import rec_pair, tight_x, MIN_SEG_FILL, MIN_SEG_H, MAX_SEGS
from q_timeline import signature

B = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(B, 'Videos')
OUT_DIR = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle_clean')


def parse_ts(ts):
    import re
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def merge_intervals(spans, gap=1.0):
    """合并重叠/邻近的窗口, 避免重复解码同一段视频。"""
    spans = sorted(spans)
    out = []
    for a, b in spans:
        if out and a - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def run_ep(ocr, ep, targets, step=4, half=3.5, paths=('bin', 'raw')):
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ivs = merge_intervals([(max(0.0, s - half), s + half) for s in targets])
    print(f'  {ep}: {len(targets)} 条 -> {len(ivs)} 个窗口, 共 '
          f'{sum(b - a for a, b in ivs):.0f}s', flush=True)

    points, n, t_ocr, n_rec = [], 0, 0.0, 0
    t0 = time.time()
    for lo, hi in ivs:
        f_lo, f_hi = int(lo * fps), min(total - 1, int(hi * fps))
        while n < f_lo:
            cap.grab()
            n += 1
        prev_sig, last = None, -10 ** 9
        while n <= f_hi:
            if not cap.grab():
                break
            if n % step == 0:
                ok, frame = cap.retrieve()
                if ok and frame is not None:
                    sig = signature(frame)
                    diff = 1.0 if prev_sig is None else float(
                        np.abs(sig.astype(np.int16) - prev_sig.astype(np.int16)).mean())
                    prev_sig = sig
                    pt = {'t': round(n / fps, 2), 'white': int(sig.sum()), 'diff': round(diff, 4)}
                    if pt['white'] == 0:
                        pt['ocr'] = False
                    elif last < f_lo or diff > 0.006:
                        last = n
                        pt['ocr'] = True
                        segs = [s for s in split_lines(frame, SCAN_TOP, SCAN_BOT)
                                if s[1] - s[0] >= MIN_SEG_H and s[2] >= MIN_SEG_FILL]
                        segs.sort(key=lambda s: -s[2])
                        recs = []
                        for y0, y1, fill in segs[:MAX_SEGS]:
                            tx = tight_x(frame, y0, y1)
                            if not tx:
                                continue
                            ta = time.time()
                            r = rec_pair(ocr, frame, y0, y1, tx, paths)
                            t_ocr += time.time() - ta
                            n_rec += len(paths)
                            recs.append(dict(r, y0=y0, y1=y1, fill=fill, x0=tx[0], x1=tx[1]))
                        pt['segs'] = recs
                    else:
                        pt['ocr'] = False
                    points.append(pt)
            n += 1
    cap.release()
    el = time.time() - t0
    out = {'ep': ep, 'fps': round(fps, 4), 'step': step, 'half': half, 'paths': list(paths),
           'n_targets': len(targets), 'n_windows': len(ivs), 'n_points': len(points),
           'n_ocr': sum(1 for p in points if p.get('ocr')), 'n_rec': n_rec,
           'elapsed': round(el, 1), 'elapsed_ocr': round(t_ocr, 1), 'points': points}
    json.dump(out, open(os.path.join(OUT_DIR, f'q_fill_{ep}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'  {ep}: 采样 {len(points)} 点 / OCR {out["n_ocr"]} 次 / {el:.0f}s', flush=True)
    return out


def main():
    args = sys.argv[1:]
    step, half = 4, 3.5
    for k in ('--step', '--half'):
        if k in args:
            j = args.index(k)
            v = float(args[j + 1])
            del args[j:j + 2]
            if k == '--step':
                step = int(v)
            else:
                half = v
    eps_arg = [a for a in args if not a.startswith('-')]
    res = json.load(open(os.path.join(OUT_DIR, 'q_unmatched_resolved.json'), encoding='utf-8'))
    todo = res['unknown'] + res['no_reading']
    by_ep = {}
    for r in todo:
        sec = parse_ts(r['ts'])
        if sec is not None:
            by_ep.setdefault(r['ep'], []).append(sec)
    eps = eps_arg or sorted(by_ep)
    print(f'补扫 {len(todo)} 条 / {len(eps)} 集 (step={step}, half={half})', flush=True)

    ocr = build_engine()
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    for ep in eps:
        if ep in by_ep:
            run_ep(ocr, ep, by_ep[ep], step, half)


if __name__ == '__main__':
    main()
