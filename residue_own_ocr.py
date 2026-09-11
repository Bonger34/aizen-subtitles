# -*- coding: utf-8 -*-
"""对 9 条未解决目标"自己那一秒"的画面做 OCR, 判断该改文本还是改图。"""
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
P = os.path.join(B, 'review', 'probe')
CROPS = {'band': (100, 880, 1820, 1050), 'lower': (100, 700, 1820, 1075),
         'low2': (100, 940, 1820, 1078)}


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


prog = json.load(open(os.path.join(B, 'review', 'shared_fix3_progress.json'), encoding='utf-8'))
todo = [v for v in prog.values() if (v.get('score') or 0) < 0.8]
ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
lines = ['9 条未解决目标: 其"自己那一秒"画面的 OCR', '']
out = []
for v in todo:
    p = os.path.join(P, f"res_{v['ep']}_{v['ts']}.jpg")
    img = cv2.imread(p)
    if img is None:
        lines.append(f"{v['ep']} {v['ts']}: 无图")
        continue
    h, w = img.shape[:2]
    sy = h / 1080.0
    got = {}
    for name, box in CROPS.items():
        for th in (245, 235, 210):
            c = img[int(box[1] * sy):int(box[3] * sy), int(box[0] * (w / 1920.0)):int(box[2] * (w / 1920.0))]
            c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
            arr = c.copy()
            mk = np.all(arr > th, axis=2)
            arr[mk] = [255, 255, 255]
            arr[~mk] = [0, 0, 0]
            try:
                r = ocr(arr)
                t = norm(''.join(r.txts) if r.txts else '')
            except Exception:
                t = ''
            if t:
                got[f'{name}/{th}'] = t
    best = max(got.values(), key=len) if got else ''
    lines.append(f"{v['ep']} {v['ts']}  库文本=[{v['text']}]")
    for k, t in got.items():
        lines.append(f'      {k}: [{t}]')
    out.append({'ep': v['ep'], 'ts': v['ts'], 'old': v['text'], 'ocr_own': got, 'best': best})
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'residue_own_ocr.txt'), 'w', encoding='utf-8').write(txt)
json.dump(out, open(os.path.join(B, 'review', 'residue_own_ocr.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(txt)
