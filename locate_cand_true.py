# -*- coding: utf-8 -*-
"""顺序读帧定位候选真身: P06 170s~215s 每 0.25s OCR, 找出「考虑下时间地点场合啊」的真实位置。"""
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
EP, T0, T1, STEP = 'P06', 170.0, 215.0, 0.25
WANT = '考虑下时间地点场合啊'


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
cap = cv2.VideoCapture(find_video(EP))
fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
cap.set(cv2.CAP_PROP_POS_FRAMES, int(T0 * fps))
n = int(T0 * fps)
next_t = T0
while next_t <= T1:
    while n / fps < next_t:
        if not cap.grab():
            break
        n += 1
    ok, fr = cap.retrieve()
    n += 1
    if not ok:
        break
    h, w = fr.shape[:2]
    sy = h / 1080.0
    c = fr[int(878 * sy):int(1075 * sy), int(100 * (w / 1920.0)):int(1820 * (w / 1920.0))]
    c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
    arr = c.copy()
    mk = np.all(arr > 245, axis=2)
    arr[mk] = [255, 255, 255]
    arr[~mk] = [0, 0, 0]
    r = ocr(arr)
    t = norm(''.join(r.txts) if r.txts else '')
    if t:
        flag = '   <<<<< 命中' if norm(WANT) in t else ''
        print(f'   {next_t:7.2f}s  [{t}]{flag}')
    next_t = round(next_t + STEP, 3)
cap.release()
