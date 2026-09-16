# -*- coding: utf-8 -*-
"""q_diag4.py — 诊断"定位到了却读不出": 打印该 1080p 帧的全部文字行段与逐段识别结果。
用法: python q_diag4.py P01 537.81
"""
import os
import sys

import cv2

import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import SCAN_TOP, SCAN_BOT, build_engine, split_lines
from q_rescan import rec_pair, tight_x

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(B, 'Videos')

ep, t = sys.argv[1], float(sys.argv[2])
vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
       if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
cap = cv2.VideoCapture(vid)
fps = cap.get(cv2.CAP_PROP_FPS)
fno = int(round(t * fps))
n = 0
while n < fno:
    cap.grab()
    n += 1
ok, frame = cap.read()
cap.release()
print(f'{ep} t={t}s fno={fno} ok={ok} shape={frame.shape}')

ocr = build_engine()
from rapidocr.ch_ppocr_rec.typings import TextRecInput
ocr.text_rec(TextRecInput(img=__import__('numpy').zeros((64, 512, 3), __import__('numpy').uint8)))

for tag, kwargs in (('无密度过滤', {}), ('密度<=0.6', {'max_density': 0.60}),
                    ('白阈值245', {'white_min': 245}), ('245+密度0.6', {'max_density': 0.60, 'white_min': 245})):
    segs = split_lines(frame, SCAN_TOP, SCAN_BOT, **kwargs)
    print(f'\n--- {tag}: {len(segs)} 段')
    for y0, y1, fill in sorted(segs, key=lambda s: -s[2])[:5]:
        area = max(1, (y1 - y0) * 1840)
        tx = tight_x(frame, y0, y1)
        txt = ''
        if tx:
            rr = rec_pair(ocr, frame, y0, y1, tx, ('bin',))
            txt = rr.get('bin') or ''
        print(f'   y{y0}-{y1} h{y1 - y0} fill={fill} 密度={fill / area:.3f} x{tx} -> [{txt}]')
