# -*- coding: utf-8 -*-
"""直接复核密集扫描保存的候选帧: 这些帧正是候选文本被读出来的画面。"""
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
FD = os.path.join(B, 'review', 'dense2_frames')
TARGETS = ['考虑下时间地点场合啊', '我早就想沐浴着阳光流流汗了', '静静地听我讲就行了',
           '一口气毁灭它', '要记得面带微笑哦', '他们的英勇奋战理应受到赞颂']


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


# 从各集候选 JSON 里找出这些文本对应的帧名
hit = {}
for f in sorted(os.listdir(os.path.join(B, 'review', 'dense2'))):
    if not f.endswith('.json'):
        continue
    d = json.load(open(os.path.join(B, 'review', 'dense2', f), encoding='utf-8'))
    for c in d['cands']:
        if c['text'] in TARGETS:
            hit.setdefault(c['text'], []).append((d['ep'], c['t'], c['frame']))

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
for t in TARGETS:
    for ep, ts, fr in hit.get(t, []):
        p = os.path.join(FD, fr)
        img = cv2.imread(p)
        if img is None:
            print(f'{t}: 帧缺失 {fr}')
            continue
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
        print(f'[{t}]  {ep} {ts}  帧={fr}')
        print(f'     带内=[{outs["band"]}]')
        print(f'     高裁=[{outs["tall"]}]')
