# -*- coding: utf-8 -*-
"""对 5 条"自己那一秒没有字幕"的目标做亚秒级密扫(0.25s × ±1s), 找它们真正的画面。"""
import json
import os
import re

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
_ORT124 = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124'
import sys
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
TARGETS = [('P06', '18m52s', '哥哥'), ('P13', '14m29s', '口'), ('P17', '18m38s', '金'),
           ('P22', '17m53s', '口'), ('P24', '18m11s', '敬告')]
CROP = (100, 880, 1820, 1078)


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
lines = ['5 条未解决目标的亚秒级密扫(0.25s × ±1s)', '']
for ep, ts, old in TARGETS:
    base = sec_of(ts)
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    lines.append(f'{ep} {ts}  库文本=[{old}]')
    for d in (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0):
        s = base + d
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(s * fps)))
        ok, fr = cap.read()
        if not ok:
            continue
        h, w = fr.shape[:2]
        sy = h / 1080.0
        c = fr[int(CROP[1] * sy):int(CROP[3] * sy), int(CROP[0] * (w / 1920.0)):int(CROP[2] * (w / 1920.0))]
        c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
        best = ''
        for th in (245, 235, 215):
            arr = c.copy()
            mk = np.all(arr > th, axis=2)
            arr[mk] = [255, 255, 255]
            arr[~mk] = [0, 0, 0]
            try:
                r = ocr(arr)
                t = norm(''.join(r.txts) if r.txts else '')
            except Exception:
                t = ''
            if len(t) > len(best):
                best = t
        lines.append(f'    {d:+.2f}s  [{best}]')
    cap.release()
    lines.append('')
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'residue_dense.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
