# -*- coding: utf-8 -*-
"""shape 假设验证: 不同文本宽度序列, 每张跑 2 次, 观察首次显著慢的时机"""
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

texts = ['爱', '爱我', '爱你的选择', '爱染诚的谜题答案就是罗布水晶', '你', '我是爱染诚的笑脸']
for t in texts:
    img = np.zeros((90, 1720, 3), dtype=np.uint8)
    cv2.putText(img, t, (150, 62), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    r1 = ''
    for k in range(2):
        t0 = time.time()
        res = ocr(img)
        dt = time.time() - t0
        r1 += f' {k}:{dt:.2f}s'
    print(f'[{t}] 字数={len(t)}{r1}', flush=True)
