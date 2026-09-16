# -*- coding: utf-8 -*-
"""sample_face_check.py — 抽样检测当前 docs/frames 帧的人脸命中情况（回答"是否人脸最优帧"）"""
import glob
import os
import random

import cv2
import numpy as np
from insightface.app import FaceAnalysis

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FRAMES_DIR = os.path.join(BASE, 'docs', 'frames')

# 随机抽 24 张（跨集）
files = sorted(glob.glob(os.path.join(FRAMES_DIR, 'P*_*m*s.jpg')))
random.seed(42)
sample = random.sample(files, min(24, len(files)))

# 主演特征库（旧管线用的）
features = np.load(os.path.join(BASE, 'face_features_insightface.npz'))
known = features['encodings']
norm_known = known / np.linalg.norm(known, axis=1, keepdims=True)

app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

n_face = n_known_hit = 0
rows = []
for f in sample:
    img = cv2.imread(f)
    if img is None:
        continue
    faces = app.get(img)
    if faces:
        n_face += 1
        best_sim = max(
            float(np.dot(f.normed_embedding, norm_known.T).max())
            for f in faces if np.linalg.norm(f.embedding) > 0
        ) if faces else 0.0
        if best_sim >= 0.4:
            n_known_hit += 1
        rows.append((os.path.basename(f), len(faces), best_sim))
    else:
        rows.append((os.path.basename(f), 0, 0.0))

print(f'抽样 {len(sample)} 帧: 有脸(任意) {n_face}，命中主演(sim>=0.4) {n_known_hit}，无脸 {len(sample)-n_face}')
for name, cnt, sim in rows[:12]:
    print(f'  {name[:34]:<36} 脸数={cnt} 主演sim={sim:.2f}')
