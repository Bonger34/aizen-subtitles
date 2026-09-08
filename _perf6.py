# -*- coding: utf-8 -*-
"""固定 rec_img_shape 实验: 不同文本序列, 每张 2 次, 观察所有帧是否稳定 ~0.6s"""
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

params = {
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH,
    'Rec.rec_img_shape': [3, 48, 640],   # 固定宽度(13 字), 消除每批动态宽
}
ocr = RapidOCR(params=params)
print('fixed shape 640', flush=True)

texts = ['爱', '你', '爱染诚的谜题答案就是罗布水晶', '爱我', '我是爱染诚的笑脸', '今天天气也很好啊']
for t in texts:
    img = np.zeros((90, 1720, 3), dtype=np.uint8)
    cv2.putText(img, t, (150, 62), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    row = ''
    for k in range(2):
        t0 = time.time()
        ocr(img)
        row += f' {k}:{time.time()-t0:.2f}s'
    print(f'[{t}] 字数={len(t)}{row}', flush=True)
