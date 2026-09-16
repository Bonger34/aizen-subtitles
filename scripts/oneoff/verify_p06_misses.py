# -*- coding: utf-8 -*-
"""核实 P06 的几条"真缺台词": 抓画面 OCR + 列出库中同时段条目。"""
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
CASES = [('P06', 2 * 60 + 43, '考虑下时间地点场合啊'), ('P06', 7 * 60 + 22, '所以就想出这个手势来了'),
         ('P06', 10 * 60 + 14, '你就特别关照我和勇海'), ('P06', 0 * 60 + 11, '我也好想试试看啊')]


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


lib = {}
for fn in os.listdir(CLEAN):
    if fn.endswith('.json'):
        lib[fn[1:4]] = [(e['timestamp'], e.get('text') or '')
                        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))]

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
cap = cv2.VideoCapture(find_video('P06'))
fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
for ep, sec, expect in CASES:
    best = ''
    for d in (0.0, 0.4, 0.8):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((sec + d) * fps)))
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
        t = norm(''.join(r.txts) if r.txts else '')
        if len(t) > len(best):
            best = t
    print(f'{ep} {sec // 60}m{sec % 60:02d}s  预期[{expect}]  画面=[{best}]')
    near = [(ts, tx) for ts, tx in lib['P06']
            if abs(int(ts.split('m')[0]) * 60 + int(ts.split('m')[1].rstrip('s')) - sec) <= 8]
    print(f'     库中 ±8s 条目: {near}')
cap.release()
