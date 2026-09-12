# -*- coding: utf-8 -*-
"""抽查"位置附近有条目、但文本全库不存在"的候选: 画面里到底有没有这句台词?"""
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
V = os.path.join(B, 'Videos')
OUT = os.path.join(B, 'review', 'probe')
CASES = [('P06', '3m06s', '考虑下时间地点场合啊'),
         ('P11', '8m55s', '他们的英勇奋战理应受到赞颂'),
         ('P18', '8m36s', '感受到恤上进发出的热情时'),
         ('P22', '10m36s', '我早就想沐浴着阳光流流汗了'),
         ('P17', '10m57s', '要记得面带微笑哦'),
         ('P19', '11m48s', '静静地听我讲就行了'),
         ('P23', '8m16s', '一口气毁灭它'),
         ('P18', '4m06s', '效果不理想啊'),
         ('P19', '0m49s', '怎么会这么闲呢'),
         ('P21', '10m53s', '之后凑澪为了从我手中逃脱'),
         ('P13', '23m28s', '总觉得爸爸今天有点奇怪'),
         ('P08', '9m33s', '奥特战士真的超棒的')]


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
for ep, ts, expect in CASES:
    s0 = sec_of(ts)
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    got, band = '', 0.0
    for d in (0.0, 0.3, 0.6, 0.9):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((s0 + d) * fps)))
        ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(fr[895:985, 100:1820], cv2.COLOR_BGR2GRAY)
        band = max(band, float((g > 245).mean()))
        h, w = fr.shape[:2]
        sy = h / 1080.0
        c = fr[int(895 * sy):int(1075 * sy), int(100 * (w / 1920.0)):int(1820 * (w / 1920.0))]
        c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
        arr = c.copy()
        mk = np.all(arr > 245, axis=2)
        arr[mk] = [255, 255, 255]
        arr[~mk] = [0, 0, 0]
        r = ocr(arr)
        t = norm(''.join(r.txts) if r.txts else '')
        if len(t) > len(got):
            got = t
        if d == 0.0:
            cv2.imwrite(os.path.join(OUT, f'chk_{ep}_{ts}.jpg'),
                        cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])
    cap.release()
    hit = norm(expect) in got or (got and sum(1 for c in norm(expect) if c in got) / len(norm(expect)) >= 0.8)
    print(f"{ep} {ts}  预期[{expect}]  {'✅画面读到' if hit else '❌画面未读到'}  OCR=[{got}]  带内={band:.3f}")
