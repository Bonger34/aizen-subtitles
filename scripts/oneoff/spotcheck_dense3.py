# -*- coding: utf-8 -*-
"""抽查"疑似漏句台词": 画面 OCR + 库中同时段条目 + 全库是否真无此句。"""
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
CLEAN = os.path.join(B, 'subtitle_clean')
CHECKS = [('P01', '3m21s'), ('P01', '3m57s'), ('P01', '5m36s'), ('P01', '5m37s'),
          ('P01', '6m45s'), ('P01', '19m56s'), ('P02', '0m20s'), ('P02', '7m25s'),
          ('P02', '17m47s'), ('P03', '0m15s')]


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


lib = {}
allt = []
for fn in os.listdir(CLEAN):
    if fn.endswith('.json'):
        ep = fn[1:4]
        lib[ep] = []
        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
            lib[ep].append((sec_of(e['timestamp']), e.get('text') or ''))
            allt.append(cn(e.get('text')))

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
caps = {}
for ep, ts in CHECKS:
    if ep not in caps:
        caps[ep] = cv2.VideoCapture(find_video(ep))
    cap = caps[ep]
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    s0 = sec_of(ts)
    seen = []
    for d in (-0.4, 0.0, 0.4):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((s0 + d) * fps)))
        ok, fr = cap.read()
        if not ok:
            continue
        h, w = fr.shape[:2]
        sy = h / 1080.0
        c = fr[int(878 * sy):int(1045 * sy), int(100 * (w / 1920.0)):int(1820 * (w / 1920.0))]
        c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
        arr = c.copy()
        mk = np.all(arr > 245, axis=2)
        arr[mk] = [255, 255, 255]
        arr[~mk] = [0, 0, 0]
        r = ocr(arr)
        seen.append(cn(''.join(r.txts) if r.txts else ''))
    near = [(t, x) for t, x in sorted(lib[ep]) if abs(t - s0) <= 6]
    print(f'{ep} {ts}  画面读到: {seen}')
    print(f'     库中 ±6s: {near}')
for cap in caps.values():
    cap.release()
