# -*- coding: utf-8 -*-
"""复现 scan_cont.py 的读取方式(字幕带裁剪 + >245 二值化 + OCR), 看漏句为何没被读到。"""
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
AREA = (100, 895, 1820, 985)          # scan_cont.py 的字幕带
CASES = [('P22', 16 * 60 + 6, '漏: 休想得逞'), ('P22', 16 * 60 + 50, '漏: 勇海我们上'),
         ('P24', 17 * 60 + 14, '漏: 明白发射牵引光束'),
         ('P22', 16 * 60 + 46, '对照: 这次就包在我们身上吧'),
         ('P24', 18 * 60 + 2, '对照: 这是最后的水晶了')]


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
for ep, s, note in CASES:
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    out = []
    for d in (0.0, 0.35, 0.7, 1.0):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((s + d) * fps)))
        ok, fr = cap.read()
        if not ok:
            continue
        crop = fr[AREA[1]:AREA[3], AREA[0]:AREA[2]]
        g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        wr = float((g > 245).mean())
        arr = crop.copy()
        mk = np.all(arr > 245, axis=2)
        arr[mk] = [255, 255, 255]
        arr[~mk] = [0, 0, 0]
        try:
            r = ocr(arr)
            t = norm(''.join(r.txts) if r.txts else '')
        except Exception as e:
            t = f'ERR {e}'
        out.append((d, round(wr, 3), t))
    cap.release()
    print(f'{ep} {s // 60}m{s % 60:02d}s  {note}')
    for d, wr, t in out:
        print(f'    +{d:.2f}s  带内白占比={wr}  OCR=[{t}]')
