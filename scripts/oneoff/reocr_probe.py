# -*- coding: utf-8 -*-
"""小样本实测: 用"扩大裁剪区"(y 850~1062)重 OCR 已存帧, 与库中现有文本对比, 判断重 OCR 的收益。

抽样策略: 一半随机, 一半取库中文本较短(<=5 字)的条目 —— 后者最可能是被裁切的碎片。
用法: python reocr_probe.py [样本数]
"""
import json
import os
import random
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
CLEAN = os.path.join(B, 'subtitle_clean')
CROP = (100, 850, 1820, 1062)
OLD_BAND = (100, 895, 1820, 985)


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9A-Za-z]', s or ''))


MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                           open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read(),
                           re.S).group(1))
lib = {}
for fn in os.listdir(CLEAN):
    m = re.match(r'\[(P\d+)\]', fn)
    if m:
        lib[fn[:-5]] = {e['timestamp']: (e.get('text') or '') for e in
                        json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))}

entries = [(k, v) for k, v in MAP.items()]
short = [(k, v) for k, v in entries
         if len(norm(lib.get(k.split('|')[0], {}).get(k.split('|')[1], ''))) <= 5]
rnd = random.Random(5).sample(entries, min(len(entries), 200))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
sample = short[:N // 2] + rnd[:N // 2]

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
print(f'样本 {len(sample)} (短文本 {min(len(short), N // 2)} + 随机 {N // 2})', flush=True)


def crop_ocr(img, box):
    h, w = img.shape[:2]
    sx, sy = w / 1920.0, h / 1080.0
    c = img[int(box[1] * sy):int(box[3] * sy), int(box[0] * sx):int(box[2] * sx)]
    c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
    arr = c.copy()
    m = np.all(arr > 245, axis=2)
    arr[m] = [255, 255, 255]
    arr[~m] = [0, 0, 0]
    res = ocr(arr)
    return norm(''.join(res.txts) if res.txts else '')


better = same = worse = 0
rows = []
for i, (key, f) in enumerate(sample):
    if i % 50 == 0:
        print(f'  {i}/{len(sample)}', flush=True)
    img = cv2.imread(os.path.join(FR, f))
    if img is None:
        continue
    title, ts = key.split('|')
    old = norm(lib.get(title, {}).get(ts, ''))
    t_old = crop_ocr(img, OLD_BAND)
    t_ext = crop_ocr(img, CROP)
    # "更好" = 新文本更长 且 旧文本基本被新文本包含(同一句, 只是补全了)
    cont = sum(1 for c in old if c in t_ext) / len(old) if old else 0
    if len(t_ext) > len(old) and cont >= 0.8:
        better += 1
        tag = '补全'
    elif t_ext == old:
        same += 1
        tag = '一致'
    else:
        worse += 1
        tag = '不同'
    rows.append((tag, key, f, old, t_old, t_ext))

lines = [f'样本 {len(rows)}: 补全 {better} / 一致 {same} / 不同 {worse}', '',
         '仅列出"补全"与"不同"的样例:']
for tag, key, f, old, t_old, t_ext in rows:
    if tag == '一致':
        continue
    lines.append(f'  [{tag}] {key}  frame={f}')
    lines.append(f'        库中文本=[{old}]  旧裁剪OCR=[{t_old}]  扩大裁剪OCR=[{t_ext}]')
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'reocr_probe.txt'), 'w', encoding='utf-8').write(txt)
print(txt[:6000])
