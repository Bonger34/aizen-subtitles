# -*- coding: utf-8 -*-
"""q_prof.py — 重扫耗时分解: 找出每帧 0.9s 花在哪里(读帧/切段/紧裁/rec)。
用法: python q_prof.py [集号]
"""
import os
import sys
import time

import cv2

import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import SCAN_TOP, SCAN_BOT, X0, X1, PAD_Y, build_engine, crop_norm, split_lines
from q_rescan import tight_x, rec_pair, MIN_SEG_H, MIN_SEG_FILL, MAX_SEGS

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(B, 'Videos')
ep = sys.argv[1] if len(sys.argv) > 1 else 'P01'
vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
       if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
cap = cv2.VideoCapture(vid)
fps = cap.get(cv2.CAP_PROP_FPS)

# 取 12 个分散时间点(避开片头片尾各 3 分钟以外的区域)
pts = [int(300 + i * 90) for i in range(12)]
frames = []
n = 0
for sec in pts:
    fno = int(sec * fps)
    while n < fno:
        cap.grab()
        n += 1
    ok, f = cap.read()
    n += 1
    if ok:
        frames.append((sec, f))
cap.release()
print(f'取帧 {len(frames)} 张')

ocr = build_engine()
t_split = t_tight = t_crop = t_bin = t_raw = 0.0
nseg = 0
for sec, f in frames:
    t0 = time.time()
    segs = [s for s in split_lines(f, SCAN_TOP, SCAN_BOT)
            if s[1] - s[0] >= MIN_SEG_H and s[2] >= MIN_SEG_FILL]
    segs.sort(key=lambda s: -s[2])
    t_split += time.time() - t0
    for y0, y1, fill in segs[:MAX_SEGS]:
        nseg += 1
        t0 = time.time()
        tx = tight_x(f, y0, y1)
        t_tight += time.time() - t0
        if not tx:
            continue
        t0 = time.time()
        c = crop_norm(f, (tx[0], y0 - PAD_Y, tx[1], y1 + PAD_Y), upscale=1.0)
        t_crop += time.time() - t0
        from rapidocr.ch_ppocr_rec.typings import TextRecInput
        t0 = time.time()
        rb = ocr.text_rec(TextRecInput(img=c))
        t_bin += time.time() - t0
        sx, sy = f.shape[1] / 1920.0, f.shape[0] / 1080.0
        raw = f[max(0, int((y0 - PAD_Y) * sy)):int((y1 + PAD_Y) * sy),
                int(tx[0] * sx):int(tx[1] * sx)]
        t0 = time.time()
        rr = ocr.text_rec(TextRecInput(img=raw))
        t_raw += time.time() - t0
        print(f'  {sec}s y{y0}-{y1} h{y1 - y0} w{tx[1] - tx[0]} crop{c.shape} '
              f'bin[{rb.txts[0] if rb.txts else ""}] raw[{rr.txts[0] if rr.txts else ""}]')
print(f'\n段数 {nseg}: split {t_split:.2f}s tight {t_tight:.2f}s crop {t_crop:.2f}s '
      f'rec_bin {t_bin:.2f}s rec_raw {t_raw:.2f}s 合计 {t_split + t_tight + t_crop + t_bin + t_raw:.2f}s')
if nseg:
    print(f'每次 rec_bin {t_bin / nseg * 1000:.0f}ms / rec_raw {t_raw / nseg * 1000:.0f}ms')
