# -*- coding: utf-8 -*-
"""抓取 3 条疑似漏句的画面 + OCR 复核。"""
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
OUT = os.path.join(B, 'review', 'probe')
CASES = [('P22', 966.0, '休想得逞'), ('P22', 1010.0, '勇海我们上'), ('P24', 1034.5, '明白发射牵引光束')]


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
for ep, s, note in CASES:
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(s * fps)))
    ok, fr = cap.read()
    cap.release()
    if not ok:
        print(f'{ep} {s}: 读帧失败')
        continue
    p = os.path.join(OUT, f'miss_{ep}_{int(s)}s.jpg')
    cv2.imwrite(p, cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                [cv2.IMWRITE_JPEG_QUALITY, 90])
    h, w = fr.shape[:2]
    sy = h / 1080.0
    t = ''
    for th in (245, 235, 215):
        c = fr[int(880 * sy):int(1062 * sy), int(100 * (w / 1920.0)):int(1820 * (w / 1920.0))]
        c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
        arr = c.copy()
        mk = np.all(arr > th, axis=2)
        arr[mk] = [255, 255, 255]
        arr[~mk] = [0, 0, 0]
        r = ocr(arr)
        tt = norm(''.join(r.txts) if r.txts else '')
        if len(tt) > len(t):
            t = tt
    print(f'{ep} {int(s) // 60}m{int(s) % 60:02d}s  预期[{note}]  OCR=[{t}]  -> {p}')
