# -*- coding: utf-8 -*-
"""
check_empty.py — 分析 OCR 空帧的成因
对抽样帧: 统计白像素占比 + 二值化 OCR 结果 + 彩色原图 OCR 结果
"""
import os
import random
import re
import sys

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
os.add_dll_directory(_NV_DLL)
os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
sys.path.insert(0, r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124')
sys.stdout.reconfigure(encoding='utf-8')

import cv2
import glob
import numpy as np
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6, 'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6, 'Rec.lang': LangRec.CH,
    'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})


def binarize(crop):
    arr = crop.copy()
    mask = np.all(arr > 245, axis=2)
    arr[mask] = [255, 255, 255]
    arr[~mask] = [0, 0, 0]
    return arr


def zh(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff]', s))


files = sorted(glob.glob(r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\review\cont_frames\P01\*_*.jpg'))
files = [f for f in files if '_s.jpg' not in f]
random.seed(42)
sample = random.sample(files, min(200, len(files)))

buckets = {'high_white_empty_bin': [], 'high_white_empty_color': [], 'low_white_empty': []}
n = 0
for f in sample:
    img = cv2.imread(f)
    if img is None:
        continue
    n += 1
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    wr = float((gray > 245).mean())
    r_bin = ocr(binarize(img))
    t_bin = zh(''.join(r_bin.txts) if r_bin.txts else '')
    if len(t_bin) > 0:
        continue
    # 空帧
    if wr < 0.02:
        buckets['low_white_empty'].append((os.path.basename(f), round(wr, 4)))
        continue
    r_col = ocr(img)   # 彩色原图
    t_col = zh(''.join(r_col.txts) if r_col.txts else '')
    key = 'high_white_empty_color' if len(t_col) > 0 else 'high_white_empty_bin'
    buckets[key].append((os.path.basename(f), round(wr, 4), t_col))
print(f'处理 {n} 帧')
print(f'低白像素空帧(噪声): {len(buckets["low_white_empty"])}')
print(f'高白像素空帧-彩色也识别不出: {len(buckets["high_white_empty_bin"])}')
print(f'高白像素空帧-彩色能识别出(二值化损失!): {len(buckets["high_white_empty_color"])}')
for x in buckets['high_white_empty_color'][:15]:
    print('   ', x)
print('高白像素样例(彩色仍空):')
for x in buckets['high_white_empty_bin'][:10]:
    print('   ', x[:2])
