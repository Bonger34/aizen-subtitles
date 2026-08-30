# -*- coding: utf-8 -*-
"""gen_anchor_aug2.py — 从已选帧提取增强锚点（快版）

替代 gen_anchor_aug.py（全 25 集 2s 剖面太慢）：
- 输入: web/frames/ 全部 4664 张台词帧（960x540）
- 对每帧取与现有锚点最大相似度 >= AUG_SIM_MIN 的人脸 embedding 加入增强集
- 查重（与已有锚点相似度 > DUP_SIM_MAX 跳过）
- 输出: face_features_aisome_aug.npz（95 基 + 增强）

台词帧本身就是「窗口最优」帧，构图覆盖各集台词场景，对评分的增益与剖面等价。
用法: python gen_anchor_aug2.py  （预计 5-8 分钟）
"""
import glob
import os

import cv2
import numpy as np
from insightface.app import FaceAnalysis

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FRAMES_DIR = os.path.join(BASE, 'web', 'frames')
AUG_SIM_MIN = 0.55
DUP_SIM_MAX = 0.985


def main():
    features = np.load(os.path.join(BASE, 'face_features_insightface.npz'))
    base = features['encodings'].astype(np.float32)
    norm_base = base / np.linalg.norm(base, axis=1, keepdims=True)
    app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    print('加载完成', flush=True)

    aug = []
    aug_norm = []
    files = sorted(glob.glob(os.path.join(FRAMES_DIR, 'P*_*m*s.jpg')))
    n_scan = n_cand = 0
    for f in files:
        img = cv2.imread(f)
        if img is None:
            continue
        n_scan += 1
        faces = app.get(img)
        best = None
        for fc in faces:
            if np.linalg.norm(fc.embedding) <= 0:
                continue
            s = float(np.dot(fc.normed_embedding, norm_base.T).max())
            if best is None or s > best[0]:
                best = (s, fc.embedding.astype(np.float32))
        if best is None or best[0] < AUG_SIM_MIN:
            continue
        n_cand += 1
        e = best[1]
        en = e / np.linalg.norm(e)
        dup = any(float(np.dot(en, en0)) > DUP_SIM_MAX for en0 in aug_norm)
        if not dup:
            aug.append(e)
            aug_norm.append(en)
        if n_scan % 500 == 0:
            print(f'... {n_scan}/{len(files)} 帧，候选 {n_cand}，增强 {len(aug)}', flush=True)

    all_emb = np.concatenate([base, np.stack(aug)], axis=0) if aug else base
    np.savez(os.path.join(BASE, 'face_features_aisome_aug.npz'), encodings=all_emb)
    print(f'完成: 基锚点 {len(base)} + 增强 {len(aug)} = {len(all_emb)} '
          f'（扫描 {n_scan} 帧，高置信候选 {n_cand}）')


if __name__ == '__main__':
    main()
