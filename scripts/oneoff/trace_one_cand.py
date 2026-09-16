# -*- coding: utf-8 -*-
"""查清一条候选的真身: 在记录位置 ±3s 内每 0.1s OCR, 看该文本到底出现在哪里。"""
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
TARGET = ('P06', 3 * 60 + 6, '考虑下时间地点场合啊', 3.0)


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
ep, base, expect, win = TARGET
cap = cv2.VideoCapture(find_video(ep))
fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
print(f'{ep} 记录位置 {base // 60}m{base % 60:02d}s  目标文本=[{expect}]  ±{win}s 每 0.1s')
d = -win
while d <= win + 1e-9:
    s = base + d
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(s * fps)))
    ok, fr = cap.read()
    if not ok:
        d += 0.1
        continue
    h, w = fr.shape[:2]
    sy = h / 1080.0
    c = fr[int(878 * sy):int(1075 * sy), int(100 * (w / 1920.0)):int(1820 * (w / 1920.0))]
    c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
    arr = c.copy()
    mk = np.all(arr > 245, axis=2)
    arr[mk] = [255, 255, 255]
    arr[~mk] = [0, 0, 0]
    r = ocr(arr)
    t = norm(''.join(r.txts) if r.txts else '')
    flag = '  <<< 命中' if norm(expect) in t else ''
    print(f'   {s:7.1f}s  [{t}]{flag}')
    d += 0.1
cap.release()

# 顺便在全库与该集内检索该文本
CLEAN = os.path.join(B, 'subtitle_clean')
fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
lib = [(e['timestamp'], e.get('text') or '') for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))]
print(f'\n库中 {ep} 3m00s~3m12s 条目:')
for ts, tx in lib:
    m = re.match(r'(\d+)m(\d+)s', ts)
    sec = int(m.group(1)) * 60 + int(m.group(2))
    if 180 <= sec <= 192:
        print(f'   {ts:>7s}  {tx}')
