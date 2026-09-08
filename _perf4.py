# -*- coding: utf-8 -*-
"""确定性与显存: 同批图跑两遍 + 期间采样 GPU 显存"""
import os
import subprocess
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
imgs = []
for t in texts:
    img = np.zeros((90, 1720, 3), dtype=np.uint8)
    cv2.putText(img, t, (150, 62), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    imgs.append(img)
# 预热一次(隔离初始化慢)
ocr(imgs[0])
for rnd in range(2):
    print(f'--- round {rnd} ---', flush=True)
    for t, img in zip(texts, imgs):
        t0 = time.time()
        ocr(img)
        print(f'  [{t}] {time.time()-t0:.2f}s', flush=True)
    # 显存采样
    o = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'],
                       capture_output=True, text=True)
    print('  显存:', o.stdout.strip().replace('\n', ' | '), flush=True)
