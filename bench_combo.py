# -*- coding: utf-8 -*-
"""bench_combo.py — 尝试多种 det/rec 组合, 测速度与可用性"""
import glob
import os
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

files = sorted(glob.glob(r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\review\cont_frames\P01\*_s.jpg'))[:12]
print('帧数', len(files), flush=True)

COMBOS = [
    ('v6 det MOBILE + CH, rec MEDIUM', dict(Det=(ModelType.MOBILE, OCRVersion.PPOCRV6, LangDet.CH),
                                            Rec=(ModelType.MEDIUM, OCRVersion.PPOCRV6, LangRec.CH))),
    ('v5 det MOBILE + MULTI, rec MEDIUM', dict(Det=(ModelType.MOBILE, OCRVersion.PPOCRV5, LangDet.MULTI),
                                               Rec=(ModelType.MEDIUM, OCRVersion.PPOCRV6, LangRec.CH))),
    ('v6 det SMALL + MULTI, rec MEDIUM', dict(Det=(ModelType.SMALL, OCRVersion.PPOCRV6, LangDet.MULTI),
                                              Rec=(ModelType.MEDIUM, OCRVersion.PPOCRV6, LangRec.CH))),
    ('v6 det TINY + MULTI, rec MEDIUM', dict(Det=(ModelType.TINY, OCRVersion.PPOCRV6, LangDet.MULTI),
                                             Rec=(ModelType.MEDIUM, OCRVersion.PPOCRV6, LangRec.CH))),
]

for name, cfg in COMBOS:
    dt_, dv, dl = cfg['Det']
    rt_, rv, rl = cfg['Rec']
    try:
        ocr = RapidOCR(params={
            'EngineConfig.onnxruntime.use_cuda': True,
            'Det.model_type': dt_, 'Det.ocr_version': dv, 'Det.lang': dl,
            'Rec.model_type': rt_, 'Rec.ocr_version': rv, 'Rec.lang': rl,
            'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
        })
        ocr(cv2.imread(files[0]))
        t0 = time.time()
        n = 0
        for f in files:
            res = ocr(cv2.imread(f))
            n += len(res.txts) if res.txts else 0
        dt = (time.time() - t0) / len(files)
        print(f'{name}: {dt:.3f}s/帧 ({n} 段文本)', flush=True)
    except Exception as e:
        print(f'{name}: 失败 {str(e)[:80]}', flush=True)
