# -*- coding: utf-8 -*-
"""verify_frames_ocr.py — 对归位帧跑 OCR, 校验帧内容与台词一致"""
import json
import os
import re
import sys

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
os.add_dll_directory(_NV_DLL)
os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
sys.path.insert(0, r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124')

import cv2
import numpy as np
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FRAMES = os.path.join(BASE, 'docs', 'frames')
AREA = (100, 895, 1820, 985)

PAIRS = [
    ('P04_0m09s.jpg', '秘密比如什么秘密啊'),
    ('P04_0m24s.jpg', '那你来说说看啊'),
    ('P10_9m59s.jpg', '好的'),
    ('P11_7m19s.jpg', '爱染'),
    ('P11_7m23s.jpg', '让市民入危险之中'),
    ('P20_24m16s.jpg', '我们互相仇视对方'),
    ('P20_24m17s.jpg', '根本不能解决问题'),
    ('P20_24m23s.jpg', '那就让我来告诉你们'),
    ('P22_4m50s.jpg', '你回来了'),
    ('P22_24m08s.jpg', '下集也要收看哦'),
    ('P25_23m26s.jpg', '你这次一定要回来啊'),
    ('P25_23m32s.jpg', '好咧'),
    ('P25_23m33s.jpg', '开工干活吧'),
    ('P25_23m36s.jpg', '那我也走'),
    ('P25_23m37s.jpg', '那我也走了'),
    ('P25_23m52s.jpg', '就到此结束了'),
]

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH,
    'Rec.rec_img_shape': [3, 48, 1536],
    'Rec.rec_batch_num': 1,
})


def norm(s):
    return re.sub(r'[^\u4e00-\u9fff]', '', s)


ok = 0
for fname, expect in PAIRS:
    img = cv2.imread(os.path.join(FRAMES, fname))
    if img is None:
        print('缺失', fname)
        continue
    # 帧是 960x540, 字幕带按比例缩放到实际高度: 895/1080*540 ≈ 447, 985/1080*540 ≈ 492
    crop = img[447:492, 50:910]
    res = ocr(crop)
    txt = ''.join(res.txts) if res.txts else ''
    got = norm(txt)
    exp = norm(expect)
    hit = exp and (exp in got or got in exp or
                   sum(1 for c in exp if c in got) / len(exp) >= 0.7)
    ok += 1 if hit else 0
    print(f'{"OK " if hit else "?? "} {fname}: 期望[{expect}] OCR[{txt}]')
print(f'\n一致 {ok}/{len(PAIRS)}')
