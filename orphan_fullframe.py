# -*- coding: utf-8 -*-
"""对"非台词"类孤儿帧做整帧 OCR: 检查是否有【不在字幕带内】的中文字幕(如次回预告卡顶部字幕)。

只处理 orphan_102_answer.txt 里未被判为"库中已有该句"的帧。
输出: 整帧 OCR 文本 + 与库的匹配情况。
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
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'Web', 'frames')
CLEAN = os.path.join(B, 'subtitle_clean')
TARGETS = ['P01_22m51s.jpg', 'P01_22m52s.jpg', 'P01_22m55s.jpg', 'P01_22m56s.jpg',
           'P01_22m57s.jpg', 'P01_22m58s.jpg', 'P18_0m56s.jpg', 'P18_1m00s.jpg',
           'P18_1m04s.jpg', 'P25_24m28s.jpg', 'P25_24m29s.jpg', 'P25_24m33s.jpg',
           'P18_1m14s.jpg', 'P08_3m35s.jpg', 'P16_2m27s.jpg', 'P16_2m29s.jpg',
           'P21_2m06s.jpg', 'P22_3m52s.jpg', 'P23_2m19s.jpg', 'P24_2m23s.jpg',
           'P21_24m03s.jpg', 'P21_24m10s.jpg',
           'P13_3m37s.jpg', 'P14_2m00s.jpg', 'P16_3m20s.jpg', 'P17_24m04s.jpg',
           'P17_24m08s.jpg', 'P20_24m07s.jpg', 'P20_24m24s.jpg', 'P22_3m21s.jpg']

lib = {}
for fn in os.listdir(CLEAN):
    m = re.match(r'\[(P\d+)\]', fn)
    if m:
        lib[m.group(1)] = [''.join(re.findall(r'[\u4e00-\u9fff]', e.get('text') or ''))
                           for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))]
allrows = [t for v in lib.values() for t in v if t]


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff]', s or ''))


def bef(tn, w):
    return sum(1 for c in tn if c in w) / len(tn) if tn and w else 0.0


ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH,
    'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
print('OCR 就绪', flush=True)
lines = ['非台词类孤儿帧 · 整帧 OCR(找字幕带之外的中文字幕):']
extra = 0
for f in TARGETS:
    p = os.path.join(FR, f)
    img = cv2.imread(p)
    if img is None:
        lines.append(f'  {f}: 读图失败')
        continue
    big = cv2.resize(img, (1920, 1080), interpolation=cv2.INTER_CUBIC)
    res = ocr(big)
    raw = ' | '.join(res.txts) if res.txts else ''
    tn = norm(raw)
    top, arg = 0.0, None
    for t in allrows:
        s = bef(tn, t) if tn else 0
        if s > top:
            top, arg = s, t
    hit = arg if top >= 0.6 else None
    if hit:
        extra += 1
    lines.append(f'  {f:18s} 整帧中文=[{tn}]  库匹配={round(top, 2)} -> {hit}')
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'orphan_fullframe.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
print(f'\n整帧 OCR 后新发现"库中已有": {extra} 帧')
