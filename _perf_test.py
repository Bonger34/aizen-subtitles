# -*- coding: utf-8 -*-
"""真实字幕 crop 帧的 OCR 性能测试: 同一实例连续 12 次计时 + 检查 GPU 显存"""
import glob
import os
import sys
import time

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
os.add_dll_directory(_NV_DLL)
os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
sys.path.insert(0, r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124')

import cv2
import numpy as np
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH})

files = sorted(glob.glob(r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\review\cont_frames\P01\*.jpg'))
print(f'帧数: {len(files)}', flush=True)
times = []
for i, f in enumerate(files[:12]):
    img = cv2.imread(f)
    t0 = time.time()
    res = ocr(img)
    dt = time.time() - t0
    times.append(dt)
    print(f'#{i+1} {os.path.basename(f)} {dt:.2f}s txt={len(res.txts) if res.txts else 0}', flush=True)
print(f'平均: {np.mean(times):.2f}s 中位: {np.median(times):.2f}s', flush=True)
