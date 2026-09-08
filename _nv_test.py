# -*- coding: utf-8 -*-
"""快速验证 CUDA EP 是否生效: 造一张白字图 OCR 计时(使用 ORT 1.24.4 cu12 DLL 链)"""
import os
import sys

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
os.add_dll_directory(_NV_DLL)
os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
sys.path.insert(0, r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124')  # ORT 1.24.4 前置

import time

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
print('OCR 初始化完成', flush=True)

# 黑底白字(模拟字幕带)
img = np.zeros((90, 1720, 3), dtype=np.uint8)
cv2.putText(img, '爱染诚的谜题答案', (200, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3)
for i in range(3):
    t0 = time.time()
    res = ocr(img)
    dt = time.time() - t0
    print(f'第{i+1}次推理耗时: {dt:.2f}s', flush=True)
print('结果:', res.txts, flush=True)
import onnxruntime as ort
print('providers:', ort.get_available_providers(), flush=True)
