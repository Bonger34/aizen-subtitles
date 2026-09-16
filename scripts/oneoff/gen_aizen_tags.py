# -*- coding: utf-8 -*-
"""gen_aizen_tags.py — 标注「画面含爱染诚」的帧

对 docs/frames 全部帧（960x540）用增强锚点(442)检测：
- max sim >= 0.4 → 该帧含爱染诚（正面/侧脸可信度足够）
输出:
  docs/aizen_frames.js    前端标记集（window.AIZEN_FRAMES）
  review/aizen_frames.json   审计副本（帧名 -> sim）
用法: python gen_aizen_tags.py   （约 5-8 分钟）
"""
import glob
import json
import os

import cv2
import numpy as np
from insightface.app import FaceAnalysis

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FRAMES_DIR = os.path.join(BASE, 'docs', 'frames')
ANCHOR = os.path.join(BASE, 'face_features_aizen_aug.npz')
HIT_MIN = 0.4


def main():
    features = np.load(ANCHOR)
    norm_known = features['encodings'] / np.linalg.norm(features['encodings'], axis=1, keepdims=True)
    print(f'锚点 {len(norm_known)}', flush=True)
    app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))

    files = sorted(glob.glob(os.path.join(FRAMES_DIR, 'P*_*m*s.jpg')))
    hits = {}      # 帧名 -> sim（仅命中）
    n = 0
    for f in files:
        img = cv2.imread(f)
        if img is None:
            continue
        n += 1
        faces = app.get(img)
        sim = 0.0
        for fc in faces:
            if np.linalg.norm(fc.embedding) <= 0:
                continue
            s = float(np.dot(fc.normed_embedding, norm_known.T).max())
            sim = max(sim, s)
        if sim >= HIT_MIN:
            hits[os.path.basename(f)] = round(sim, 3)
        if n % 500 == 0:
            print(f'... {n}/{len(files)}，当前命中 {len(hits)}', flush=True)

    # 前端标记集（只保留帧名，体积最小）
    js = 'window.AIZEN_FRAMES = ' + json.dumps({k: 1 for k in hits},
                                                ensure_ascii=False, separators=(',', ':')) + ';'
    with open(os.path.join(BASE, 'docs', 'aizen_frames.js'), 'w', encoding='utf-8') as fh:
        fh.write(js)
    with open(os.path.join(BASE, 'review', 'aizen_frames.json'), 'w', encoding='utf-8') as fh:
        json.dump(hits, fh, ensure_ascii=False, indent=0)
    print(f'完成: 扫描 {n} 帧，含爱染诚 {len(hits)} 帧（{len(hits)/n*100:.1f}%）')


if __name__ == '__main__':
    main()
