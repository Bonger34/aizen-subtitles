# -*- coding: utf-8 -*-
"""对最后 2 条残留做分档扩窗 + 密集扫描。

分档(命中即停): ±10s@0.25s  ->  ±30s@0.5s  ->  ±120s@1s
每个位置试 4 种裁剪 × 3 种阈值:
  band (100, 880,1820,1050)  字幕带及下方
  low  (100, 700,1820,1078)  下半屏
  top  (100,  40,1820, 300)  画面上部(标牌/卡片)
  full (   0,   0,1920,1080) 整屏
判据: OCR 结果**包含**目标文本(子串) 或 包含度 >= 0.8。
"""
import json
import os
import re
import sys

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
_ORT124 = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124'
if os.path.isdir(_NV_DLL):
    os.add_dll_directory(_NV_DLL)
    os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
if os.path.isdir(_ORT124):
    sys.path.insert(0, _ORT124)

import cv2
import numpy as np
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
OUT = os.path.join(B, 'review', 'residue_widen.txt')
TARGETS = [('P22', '17m53s', '口'), ('P24', '18m11s', '敬告')]
CROPS = {'band': (100, 880, 1820, 1050), 'low': (100, 700, 1820, 1078),
         'top': (100, 40, 1820, 300), 'full': (0, 0, 1920, 1080)}
STAGES = [(10, 0.25), (30, 0.5), (120, 1.0)]


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def crop_for(frame, box):
    h, w = frame.shape[:2]
    sy = h / 1080.0
    c = frame[int(box[1] * sy):int(box[3] * sy), int(box[0] * (w / 1920.0)):int(box[2] * (w / 1920.0))]
    return cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)


ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
lines = ['最后 2 条残留: 分档扩窗 + 密集扫描', '']
for ep, ts, want_raw in TARGETS:
    base = sec_of(ts)
    want = norm(want_raw)
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    dur = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
    lines.append(f'=== {ep} {ts}  目标文本=[{want_raw}]  (片长 {int(dur) // 60}m{int(dur) % 60:02d}s)')
    found = []
    for win, step in STAGES:
        hits = []
        d = -win
        while d <= win + 1e-9:
            s = base + d
            if 0 <= s <= dur:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(s * fps)))
                ok, fr = cap.read()
                if ok:
                    for cname, box in CROPS.items():
                        cr = crop_for(fr, box)
                        for th in (245, 235, 215):
                            arr = cr.copy()
                            mk = np.all(arr > th, axis=2)
                            arr[mk] = [255, 255, 255]
                            arr[~mk] = [0, 0, 0]
                            try:
                                rr = ocr(arr)
                                got = norm(''.join(rr.txts) if rr.txts else '')
                            except Exception:
                                got = ''
                            if not got:
                                continue
                            cont = sum(1 for ch in want if ch in got) / len(want)
                            if want in got or cont >= 0.8:
                                hits.append((round(d, 2), cname, th, got))
            d += step
        lines.append(f'  档 ±{win}s@{step}s: 命中 {len(hits)}')
        for h in hits[:12]:
            lines.append(f'      {h[0]:+7.2f}s  {h[1]:4s}/{h[2]}  [{h[3]}]')
        if hits:
            found = hits
            break
    if not found:
        lines.append('  三档扫描均未命中')
    cap.release()
    lines.append('')
txt = '\n'.join(lines)
open(OUT, 'w', encoding='utf-8').write(txt)
print(txt)
