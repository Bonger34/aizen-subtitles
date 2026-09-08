# -*- coding: utf-8 -*-
"""显存与慢帧关系: OCR 会话内边推理边采样 nvidia-smi 显存 + 每帧计时"""
import os
import subprocess
import sys
import threading
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

mem_log = []
stop = threading.Event()


def poll():
    while not stop.is_set():
        o = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu', '--format=csv,noheader,nounits'],
                           capture_output=True, text=True)
        mem_log.append(o.stdout.strip())
        time.sleep(1)


th = threading.Thread(target=poll, daemon=True)
th.start()

texts = ['爱', '你', '爱染诚的谜题答案就是罗布水晶', '爱我', '我是爱染诚的笑脸']
for t in texts:
    img = np.zeros((90, 1720, 3), dtype=np.uint8)
    cv2.putText(img, t, (150, 62), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    t0 = time.time()
    ocr(img)
    print(f'[{t}] {time.time()-t0:.2f}s', flush=True)
stop.set()
th.join()
print('显存采样尾10条:')
for m in mem_log[-10:]:
    print(' ', m, flush=True)
