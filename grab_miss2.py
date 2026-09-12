# -*- coding: utf-8 -*-
"""抓取 18 条"高度疑似真漏"位置附近的画面并 OCR, 判定是否为真字幕。"""
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
CASES = [('P04', '18m47s'), ('P16', '15m52s'), ('P08', '23m17s'), ('P12', '22m51s'),
         ('P15', '1m42s'), ('P12', '23m14s'), ('P18', '1m16s'), ('P18', '1m09s'),
         ('P18', '1m14s'), ('P08', '22m39s'), ('P18', '1m11s'), ('P18', '24m00s'),
         ('P20', '22m42s'), ('P20', '22m45s')]


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
for ep, ts in CASES:
    s0 = sec_of(ts)
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    best = ''
    band = 0.0
    for d in (0.0, 0.3, 0.6):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((s0 + d) * fps)))
        ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(fr[895:985, 100:1820], cv2.COLOR_BGR2GRAY)
        band = max(band, float((g > 245).mean()))
        h, w = fr.shape[:2]
        sy = h / 1080.0
        c = fr[int(878 * sy):int(1075 * sy), int(100 * (w / 1920.0)):int(1820 * (w / 1920.0))]
        c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
        for th in (245, 235):
            arr = c.copy()
            mk = np.all(arr > th, axis=2)
            arr[mk] = [255, 255, 255]
            arr[~mk] = [0, 0, 0]
            r = ocr(arr)
            t = norm(''.join(r.txts) if r.txts else '')
            if len(t) > len(best):
                best = t
        if d == 0.0:
            cv2.imwrite(os.path.join(OUT, f'miss2_{ep}_{ts}.jpg'),
                        cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])
    cap.release()
    print(f'{ep} {ts}  带内白占比={band:.3f}  OCR=[{best}]  图=miss2_{ep}_{ts}.jpg')
