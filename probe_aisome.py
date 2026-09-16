# -*- coding: utf-8 -*-
"""probe_aisome.py — 诊断爱染诚命中率

问题背景：全量帧统计爱染诚命中率仅 8.7%，需区分两种可能：
1) 剧集本身台词期间爱染诚出现少（物理在场率低）→ 命中率合理
2) 抽帧/评分逻辑有缺陷，漏掉了在场爱染诚 → 需要修

做法：
A) 全剖面：对指定集每 2s 抽一帧（1080p 原帧），统计与爱染诚锚点(95张)的
   最大相似度分布 → 得到「爱染诚在该集画面中的真实占比」
B) 已选帧：统计该集 docs/frames 现有帧（960x540 缩略图）的相似度分布 →
   得到「台词期间命中率」，与 A 对比。

用法: python probe_aisome.py [P01] [P03] ...   （不带参数 = 默认 P03 P11 P01 P19 P24）
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
FRAMES_DIR = os.path.join(BASE, 'docs', 'frames')
REVIEW_DIR = os.path.join(BASE, 'review')
SAMPLE_SEC = 2          # 全剖面采样间隔（秒）
EPS = ('P01', 'P03', 'P11', 'P19', 'P24')


def max_sim(faces, norm_known):
    """一帧内所有人脸与爱染诚锚点的最大相似度。"""
    sims = [float(np.dot(fc.normed_embedding, norm_known.T).max())
            for fc in faces if np.linalg.norm(fc.embedding) > 0]
    return max(sims) if sims else 0.0


def bucket_of(sim, has_face):
    """相似度分桶（与 face_stats_all 一致）。"""
    if not has_face:
        return 'no_face'
    if sim >= 0.5:
        return 'geq05'
    if sim >= 0.4:
        return '04_05'
    if sim >= 0.3:
        return '03_04'
    if sim >= 0.15:
        return '015_03'
    return 'lt015'


def main():
    eps = sys.argv[1:] or list(EPS)
    print('加载锚点 + InsightFace...', flush=True)
    features = np.load(os.path.join(BASE, 'face_features_insightface.npz'))
    norm_known = features['encodings'] / np.linalg.norm(features['encodings'], axis=1, keepdims=True)
    app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    print('加载完成', flush=True)

    report = {}
    for ep in eps:
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            print(f'{ep}: 无视频，跳过')
            continue

        # ---- A) 全剖面 ----
        cap = cv2.VideoCapture(video[0])
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
        prof = []
        t = 0
        while t < dur:
            cap.set(cv2.CAP_PROP_POS_MSEC, int(t * 1000))
            ret, frame = cap.read()
            if ret is None or frame is None:
                t += SAMPLE_SEC
                continue
            faces = app.get(frame)
            sim = max_sim(faces, norm_known)
            prof.append((round(t, 1), sim))
            t += SAMPLE_SEC
        cap.release()
        hit = sum(1 for _, s in prof if s >= 0.4)
        buckets = {k: sum(1 for _, s in prof if bucket_of(s, True) == k) for k in
                   ('geq05', '04_05', '03_04', '015_03', 'lt015')}
        buckets['no_face'] = sum(1 for _, s in prof if s == 0.0)
        # 记录一些「爱染诚在场」的时刻便于抽查（sim 最高前 8 个）
        top = sorted(prof, key=lambda x: -x[1])[:8]
        report[ep] = {
            'profile_n': len(prof),
            'profile_hit_ge04': hit,
            'profile_hit_pct': round(hit / len(prof) * 100, 1) if prof else 0,
            'profile_buckets': buckets,
            'profile_top': [(t, round(s, 3)) for t, s in top],
        }
        print(f'{ep}: 剖面 n={len(prof)}  命中(sim>=0.4)={hit} '
              f'({hit / len(prof) * 100:.1f}%)  buckets={buckets}', flush=True)

        # ---- B) 已选帧 ----
        files = sorted([f for f in os.listdir(FRAMES_DIR) if re.match(rf'^{ep}_\d+m\d+s\.jpg$', f)])
        sel = {}
        for f in files:
            img = cv2.imread(os.path.join(FRAMES_DIR, f))
            if img is None:
                continue
            faces = app.get(img)
            sim = max_sim(faces, norm_known)
            sel[f] = sim
        hit_s = sum(1 for s in sel.values() if s >= 0.4)
        sb = {k: sum(1 for s in sel.values() if bucket_of(s, True) == k) for k in
              ('geq05', '04_05', '03_04', '015_03', 'lt015')}
        sb['no_face'] = sum(1 for s in sel.values() if s == 0.0)
        top_s = sorted(sel.items(), key=lambda x: -x[1])[:8]
        report[ep]['sel_n'] = len(sel)
        report[ep]['sel_hit_ge04'] = hit_s
        report[ep]['sel_hit_pct'] = round(hit_s / len(sel) * 100, 1) if sel else 0
        report[ep]['sel_buckets'] = sb
        report[ep]['sel_top'] = [(f, round(s, 3)) for f, s in top_s]
        print(f'{ep}: 已选帧 n={len(sel)}  命中={hit_s} ({hit_s / len(sel) * 100:.1f}%)  '
              f'buckets={sb}', flush=True)

    out = os.path.join(REVIEW_DIR, 'probe_aisome.json')
    json.dump(report, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'\n结果已保存: {out}')


if __name__ == '__main__':
    main()
