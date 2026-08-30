# -*- coding: utf-8 -*-
"""gen_anchor_aug.py — 从全 25 集 2s 剖面提取增强锚点

原理：当前 95 张爱染诚锚点覆盖面有限（不同镜头/角度/妆造），
用「与现有锚点最大相似度 >= AUG_SIM_MIN 的剖面人脸 embedding」补充锚点集，
这些高置信人脸极大概率就是爱染诚，可显著提升边缘镜头的识别率。

输出: face_features_aisome_aug.npz（encodings = 95 基锚点 + 增强锚点）
用法: python gen_anchor_aug.py   （后台运行，约 25 集 × 736 帧 ≈ 15 分钟）
"""
import json
import os
import re

import cv2
import numpy as np
from insightface.app import FaceAnalysis

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO_DIR = os.path.join(BASE, 'Videos')
SAMPLE_SEC = 2
AUG_SIM_MIN = 0.55        # 高置信阈值：低于此不选入锚点
DUP_SIM_MAX = 0.985       # 与已有锚点相似度超过此值视为重复，跳过


def main():
    features = np.load(os.path.join(BASE, 'face_features_insightface.npz'))
    base = features['encodings'].astype(np.float32)
    norm_base = base / np.linalg.norm(base, axis=1, keepdims=True)

    app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    print('加载完成', flush=True)

    aug = []       # 增强锚点（未归一化保存，调用处再归一化）
    aug_norm = []  # 归一化后的，用于查重
    per_ep = {}
    vids = sorted([v for v in os.listdir(VIDEO_DIR) if v.lower().endswith('.mp4')])
    for v in vids:
        ep = v.split(']')[0].lstrip('[')
        cap = cv2.VideoCapture(os.path.join(VIDEO_DIR, v))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
        n_add = 0
        t = 0
        while t < dur:
            cap.set(cv2.CAP_PROP_POS_MSEC, int(t * 1000))
            ret, frame = cap.read()
            if frame is None:
                t += SAMPLE_SEC
                continue
            faces = app.get(frame)
            best = None
            for f in faces:
                if np.linalg.norm(f.embedding) <= 0:
                    continue
                s = float(np.dot(f.normed_embedding, norm_base.T).max())
                if best is None or s > best[0]:
                    best = (s, f.embedding.astype(np.float32))
            if best is not None and best[0] >= AUG_SIM_MIN:
                e = best[1]
                en = e / np.linalg.norm(e)
                # 与已有锚点（基 + 已增）查重，避免大量重复帧
                dup = False
                for en0 in aug_norm:
                    if float(np.dot(en, en0)) > DUP_SIM_MAX:
                        dup = True
                        break
                if not dup:
                    aug.append(e)
                    aug_norm.append(en)
                    n_add += 1
            t += SAMPLE_SEC
        cap.release()
        per_ep[ep] = n_add
        print(f'{ep}: 本集新增 {n_add}（累计 {len(aug)}）', flush=True)

    all_emb = np.concatenate([base, np.stack(aug)], axis=0) if aug else base
    np.savez(os.path.join(BASE, 'face_features_aisome_aug.npz'), encodings=all_emb)
    json.dump(per_ep, open(os.path.join(BASE, 'review', 'anchor_aug_per_ep.json'), 'w',
                           encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'完成: 基锚点 {len(base)} + 增强 {len(aug)} = {len(all_emb)}，'
          f'保存 face_features_aisome_aug.npz')


if __name__ == '__main__':
    main()
