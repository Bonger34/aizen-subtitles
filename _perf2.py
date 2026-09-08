# -*- coding: utf-8 -*-
"""慢速根因调查: 同一帧连续 OCR 3 次; 打印 RapidOCR 内部对象结构"""
import os
import sys
import time

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
os.add_dll_directory(_NV_DLL)
os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
sys.path.insert(0, r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124')

import cv2
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH})

# 内部结构探察
for k, v in ocr.__dict__.items():
    print('attr:', k, type(v).__name__, flush=True)

img = cv2.imread(r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\review\cont_frames\P01\P01_000084_1.jpg')
for i in range(7):
    t0 = time.time()
    res = ocr(img)
    print(f'run{i} {time.time()-t0:.2f}s txts={res.txts if res.txts else []}', flush=True)
