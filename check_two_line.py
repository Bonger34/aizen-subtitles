# -*- coding: utf-8 -*-
"""验证猜测: 候选文本是不是"两行字幕里库只记了第一行"的第二行。

做法: 找到候选的最近库条目的配图帧, 用高裁剪(y 860~1075)OCR, 看候选文本是否出现在同一帧里。
"""
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
FR = os.path.join(B, 'docs', 'frames')
MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                           open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read(),
                           re.S).group(1))
CASES = [('P06', '你好歹也考虑下当下的潮流嘛', '考虑下时间地点场合啊'),
         ('P22', '搞不好以后就流行了', '我早就想沐浴着阳光流流汗了'),
         ('P19', '你一直希望孩子们长大后', '静静地听我讲就行了'),
         ('P23', '一口一城商', '一口气毁灭它')]


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
for ep, libtext, cand in CASES:
    key = [k for k in MAP if k.startswith(f'[{ep}]') and libtext in k]
    if not key:
        print(f'{ep} 「{libtext}」 不在库中');
        continue
    f = MAP[key[0]]
    img = cv2.imread(os.path.join(FR, f))
    h, w = img.shape[:2]
    sy = h / 1080.0
    outs = {}
    for name, box in (('band', (100, 895, 1820, 985)), ('tall', (100, 860, 1820, 1075))):
        c = img[int(box[1] * sy):int(box[3] * sy), int(box[0] * (w / 1920.0)):int(box[2] * (w / 1920.0))]
        c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
        arr = c.copy()
        mk = np.all(arr > 245, axis=2)
        arr[mk] = [255, 255, 255]
        arr[~mk] = [0, 0, 0]
        r = ocr(arr)
        outs[name] = norm(''.join(r.txts) if r.txts else '')
    print(f'{ep} 库条目[{libtext}] 配图={f}')
    print(f'     带内裁剪 OCR=[{outs["band"]}]')
    print(f'     高裁剪   OCR=[{outs["tall"]}]   候选[{cand}]在其中={"是" if norm(cand) in outs["tall"] else "否"}')
