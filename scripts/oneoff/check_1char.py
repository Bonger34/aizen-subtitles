# -*- coding: utf-8 -*-
"""check_1char.py — 抽样重 OCR 密集采样帧, 统计被 len<2 过滤掉的单字结果"""
import os
import random
import re
import sys

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
os.add_dll_directory(_NV_DLL)
os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
sys.path.insert(0, r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124')
sys.stdout.reconfigure(encoding='utf-8')

import cv2
import glob
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6, 'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6, 'Rec.lang': LangRec.CH,
    'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})


def binarize(crop):
    import numpy as np
    arr = crop.copy()
    mask = np.all(arr > 245, axis=2)
    arr[mask] = [255, 255, 255]
    arr[~mask] = [0, 0, 0]
    return arr


files = sorted(glob.glob(r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\review\cont_frames\P01\*_*.jpg'))
files = [f for f in files if '_s.jpg' not in f]
random.seed(42)
sample = random.sample(files, min(300, len(files)))
print('抽样帧数', len(sample), flush=True)

one_char = []
empty = 0
n = 0
for f in sample:
    img = cv2.imread(f)
    if img is None:
        continue
    res = ocr(binarize(img))
    txt = ''.join(res.txts) if res.txts else ''
    tn = ''.join(re.findall(r'[\u4e00-\u9fff]', txt))
    n += 1
    if len(tn) == 0:
        empty += 1
    elif len(tn) == 1:
        one_char.append(tn)
print(f'处理 {n} 帧: 空 {empty} ({empty/n:.1%}), 单字 {len(one_char)} ({len(one_char)/n:.1%})')
print('单字样本:', one_char[:40])
