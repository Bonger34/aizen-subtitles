# -*- coding: utf-8 -*-
"""bench_scale.py — 测试 crop 缩放对速度与识别一致性的影响"""
import glob
import os
import re
import sys
import time

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
os.add_dll_directory(_NV_DLL)
os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
sys.path.insert(0, r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124')
sys.stdout.reconfigure(encoding='utf-8')

import cv2
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

files = sorted(glob.glob(r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\review\cont_frames\P01\*_s.jpg'))[:25]
ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6, 'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6, 'Rec.lang': LangRec.CH,
    'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})


def norm(s):
    return re.sub(r'[^\u4e00-\u9fff]', '', s)


# 基准(原尺寸)
ocr(cv2.imread(files[0]))
t0 = time.time()
base_txt = []
for f in files:
    res = ocr(cv2.imread(f))
    base_txt.append(norm(''.join(res.txts) if res.txts else ''))
t_base = (time.time() - t0) / len(files)
print(f'原尺寸 1720x90: {t_base:.3f}s/帧', flush=True)

for scale in [0.7, 0.5]:
    t0 = time.time()
    txts = []
    for f in files:
        img = cv2.imread(f)
        h, w = img.shape[:2]
        img2 = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        res = ocr(img2)
        txts.append(norm(''.join(res.txts) if res.txts else ''))
    t_s = (time.time() - t0) / len(files)
    same = sum(1 for a, b in zip(base_txt, txts) if a == b)
    print(f'缩放 {scale}: {t_s:.3f}s/帧, 文本完全一致 {same}/{len(files)}', flush=True)
    for a, b in list(zip(base_txt, txts))[:8]:
        if a != b:
            print(f'   差异: 原[{a}] -> 缩放[{b}]', flush=True)
