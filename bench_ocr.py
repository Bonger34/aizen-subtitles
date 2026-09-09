# -*- coding: utf-8 -*-
"""bench_ocr.py — 测不同模型组合的速度(真实字幕帧)"""
import os
import sys
import time

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
os.add_dll_directory(_NV_DLL)
os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
sys.path.insert(0, r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124')

import cv2
import glob
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

files = sorted(glob.glob(r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\review\cont_frames\P01\*_s.jpg'))[:30]
print('测试帧数', len(files))


def bench(name, params):
    ocr = RapidOCR(params=params)
    # warmup
    img = cv2.imread(files[0])
    ocr(img)
    t0 = time.time()
    n_txt = 0
    for f in files:
        img = cv2.imread(f)
        res = ocr(img)
        n_txt += len(res.txts) if res.txts else 0
    dt = time.time() - t0
    print(f'{name}: {dt/len(files):.3f}s/帧, 共 {n_txt} 段文本', flush=True)


base = {
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.lang': LangDet.MULTI,
    'Rec.lang': LangRec.CH,
    'Rec.rec_img_shape': [3, 48, 1536],
    'Rec.rec_batch_num': 1,
}
bench('medium det + medium rec(当前)', dict(base, **{
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6}))
bench('mobile det + medium rec', dict(base, **{
    'Det.model_type': ModelType.MOBILE, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6}))
bench('mobile det + mobile rec', dict(base, **{
    'Det.model_type': ModelType.MOBILE, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Rec.model_type': ModelType.MOBILE, 'Rec.ocr_version': OCRVersion.PPOCRV6}))
