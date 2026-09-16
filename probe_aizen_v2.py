# -*- coding: utf-8 -*-
"""probe_aizen_v2.py — 提升爱染诚命中率的对照实验

对比 baseline（det 640 + 全 95 锚点）与改进（det 1280 + 精选锚点）：
- 精选锚点：锚点自检相似度矩阵里与其他锚点平均相似度 < 0.55 的坏图剔除
  （63x89 侧脸小图 etc. 会拉低真实爱染诚的匹配分）
- det_size 1280：1080p 原帧不再被压到 1/3，中远景小脸召回提升
- 另测 0.5s 步长对窗口内逐帧细扫的增益（用已选帧模拟：同秒内多帧取最优）

用法: python probe_aizen_v2.py [P03 P11 ...]（默认 P03 P11）
"""
import json
import os
import re
import sys

import cv2
import numpy as np
from insightface.app import FaceAnalysis

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES_DIR = os.path.join(BASE, 'web', 'frames')
REVIEW_DIR = os.path.join(BASE, 'review')
SAMPLE_SEC = 2
ANCHOR_MEAN_MIN = 0.55   # 锚点精选阈值：与其他锚点平均相似度


def select_anchors(enc):
    """返回精选锚点子集（剔除与锚点集平均相似度低于阈值的坏图）。"""
    e = enc / np.linalg.norm(enc, axis=1, keepdims=True)
    S = e @ e.T
    n = S.shape[0]
    keep = []
    for i in range(n):
        row = np.delete(S[i], i)
        if row.mean() >= ANCHOR_MEAN_MIN:
            keep.append(i)
    return enc[keep]


def max_sim(faces, norm_known):
    sims = [float(np.dot(fc.normed_embedding, norm_known.T).max())
            for fc in faces if np.linalg.norm(fc.embedding) > 0]
    return max(sims) if sims else 0.0


def main():
    eps = sys.argv[1:] or ['P03', 'P11']
    features = np.load(os.path.join(BASE, 'face_features_insightface.npz'))
    enc = features['encodings']
    sel = select_anchors(enc)
    norm_sel = sel / np.linalg.norm(sel, axis=1, keepdims=True)
    print(f'锚点精选: {len(enc)} → {len(sel)} 张', flush=True)
    app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(1280, 1280))
    print('加载完成（det 1280）', flush=True)

    report = {}
    for ep in eps:
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            continue
        cap = cv2.VideoCapture(video[0])
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
        prof = []
        t = 0
        while t < dur:
            cap.set(cv2.CAP_PROP_POS_MSEC, int(t * 1000))
            ret, frame = cap.read()
            if frame is None:
                t += SAMPLE_SEC
                continue
            faces = app.get(frame)
            sim = max_sim(faces, norm_sel)
            prof.append((round(t, 1), sim))
            t += SAMPLE_SEC
        cap.release()
        n = len(prof)
        hit = sum(1 for _, s in prof if s >= 0.4)
        buckets = {k: sum(1 for _, s in prof if (0.0 < s) and (
            k == ('geq05' if s >= 0.5 else '04_05' if s >= 0.4 else
                  '03_04' if s >= 0.3 else '015_03' if s >= 0.15 else 'lt015')))
            for k in ('geq05', '04_05', '03_04', '015_03', 'lt015')}
        buckets['no_face'] = n - sum(buckets.values())
        report[ep] = {
            'profile_n': n, 'profile_hit_ge04': hit,
            'profile_hit_pct': round(hit / n * 100, 1) if n else 0,
            'profile_buckets': buckets,
        }
        print(f'{ep}: 剖面(det1280+精选锚点) n={n} 命中={hit} ({hit / n * 100:.1f}%) '
              f'buckets={buckets}', flush=True)
        # 已选帧（960x540 缩略图，同样 det1280 口径）
        files = sorted([f for f in os.listdir(FRAMES_DIR)
                        if re.match(rf'^{ep}_\d+m\d+s\.jpg$', f)])
        sims = {}
        for f in files:
            img = cv2.imread(os.path.join(FRAMES_DIR, f))
            if img is None:
                continue
            faces = app.get(img)
            sims[f] = max_sim(faces, norm_sel)
        hs = sum(1 for s in sims.values() if s >= 0.4)
        bs = {k: sum(1 for s in sims.values() if (0.0 < s) and (
            k == ('geq05' if s >= 0.5 else '04_05' if s >= 0.4 else
                  '03_04' if s >= 0.3 else '015_03' if s >= 0.15 else 'lt015')))
            for k in ('geq05', '04_05', '03_04', '015_03', 'lt015')}
        bs['no_face'] = len(sims) - sum(bs.values())
        report[ep]['sel_n'] = len(sims)
        report[ep]['sel_hit_ge04'] = hs
        report[ep]['sel_hit_pct'] = round(hs / len(sims) * 100, 1) if sims else 0
        report[ep]['sel_buckets'] = bs
        print(f'{ep}: 已选帧 n={len(sims)} 命中={hs} ({hs / len(sims) * 100:.1f}%) '
              f'buckets={bs}', flush=True)

    out = os.path.join(REVIEW_DIR, 'probe_aizen_v2.json')
    json.dump(report, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'\n保存: {out}')


if __name__ == '__main__':
    main()
