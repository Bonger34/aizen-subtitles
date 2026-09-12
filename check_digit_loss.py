# -*- coding: utf-8 -*-
"""核实 3 条"库里掉了数字"的条目: 抓库条目的配图帧并 OCR, 看画面是否有数字。"""
import json
import os
import re
import sys

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
_ORT124 = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124'
if os.path.isdir(_NV_DLL):
    os.add_dll_directory(_NV_DLL)
    os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
if os.path.isdir(_ORT124):
    sys.path.insert(0, _ORT124)

import cv2
import numpy as np
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'Web', 'frames')
CLEAN = os.path.join(B, 'subtitle_clean')
MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                           open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read(),
                           re.S).group(1))
Q = ['年前绫香星从天而降', '周期为年的椭圆轨道', '然而那之后又过了年']
CROP = (100, 880, 1820, 1062)


def cn(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
for fn in sorted(os.listdir(CLEAN)):
    if not fn.endswith('.json'):
        continue
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        t = cn(e.get('text'))
        if t in Q:
            key = f"{fn[:-5]}|{e['timestamp']}"
            f = MAP.get(key)
            img = cv2.imread(os.path.join(FR, f)) if f else None
            got = ''
            if img is not None:
                h, w = img.shape[:2]
                sy = h / 1080.0
                c = img[int(CROP[1] * sy):int(CROP[3] * sy), int(CROP[0] * (w / 1920.0)):int(CROP[2] * (w / 1920.0))]
                c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
                arr = c.copy()
                mk = np.all(arr > 245, axis=2)
                arr[mk] = [255, 255, 255]
                arr[~mk] = [0, 0, 0]
                r = ocr(arr)
                got = cn(''.join(r.txts) if r.txts else '')
            print(f"{fn[1:4]} {e['timestamp']:>7s} 库文本=[{e.get('text')}] 配图={f} 画面OCR=[{got}]")
