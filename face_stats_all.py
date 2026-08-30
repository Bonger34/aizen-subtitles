# -*- coding: utf-8 -*-
"""face_stats_all.py — 全量统计 web/frames 帧的主演命中分布（方案C验收）"""
import glob
import os
import sys

import cv2
import numpy as np
from insightface.app import FaceAnalysis

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FRAMES_DIR = os.path.join(BASE, 'web', 'frames')
# 默认用增强锚点（95 基 + 全 25 集高置信爱染诚），可用 --base 切回原锚点
ANCHOR = 'face_features_aisome_aug.npz'
if '--base' in sys.argv:
    ANCHOR = 'face_features_insightface.npz'

app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
features = np.load(os.path.join(BASE, ANCHOR))
norm_known = features['encodings'] / np.linalg.norm(features['encodings'], axis=1, keepdims=True)

files = sorted(glob.glob(os.path.join(FRAMES_DIR, 'P*_*m*s.jpg')))
buckets = {'geq05': 0, '04_05': 0, '03_04': 0, '015_03': 0, 'lt015': 0, 'no_face': 0}
n = 0
for f in files:
    img = cv2.imread(f)
    if img is None:
        continue
    faces = app.get(img)
    n += 1
    if not faces:
        buckets['no_face'] += 1
    else:
        sim = max((float(np.dot(fc.normed_embedding, norm_known.T).max())
                   for fc in faces if np.linalg.norm(fc.embedding) > 0), default=0.0)
        if sim >= 0.5:
            buckets['geq05'] += 1
        elif sim >= 0.4:
            buckets['04_05'] += 1
        elif sim >= 0.3:
            buckets['03_04'] += 1
        elif sim >= 0.15:
            buckets['015_03'] += 1
        else:
            buckets['lt015'] += 1
    if n % 500 == 0:
        print(f'... {n}/{len(files)}', flush=True)

print(f'总帧 {n}')
for k in ('geq05', '04_05', '03_04', '015_03', 'lt015', 'no_face'):
    c = buckets[k]
    print(f'  {k:<7} {c:>5}  {c / n * 100:5.1f}%')
hit = buckets['geq05'] + buckets['04_05']
print(f'主演命中(sim>=0.4): {hit} ({hit / n * 100:.1f}%)')
