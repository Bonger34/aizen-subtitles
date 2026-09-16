# -*- coding: utf-8 -*-
"""probe_aizen_v3.py — 命中率提升实验（P03 精测）

实验 A：0.5s 步长窗口细扫（vs 现 1s 步长 + 800ms 偏移）
  对每条字幕的显示窗口按 0.5s 采样，OCR 校验 + 爱染诚 sim 评分，取最优帧；
  与当前已选帧（1s 版）对比命中率。

实验 B：锚点自增强
  P03 剖面中 sim>=0.55 的人脸 embedding 补充进锚点集（覆盖不同角度/妆造），
  用增强锚点重新给已选帧评分，对比命中率。

用法: python probe_aizen_v3.py [P03]（默认 P03）
"""
import json
import os
import re
import sys

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from rapidocr_onnxruntime import RapidOCR

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES_DIR = os.path.join(BASE, 'web', 'frames')
REVIEW_DIR = os.path.join(BASE, 'review')
SUBTITLE_AREA = (100, 895, 1820, 985)
SAMPLE_SEC = 2
STEP = 0.5          # 细扫步长（秒）
WINDOW_MAX = 3
WINDOW_GAP = 1
AUG_SIM_MIN = 0.55  # 自增强锚点选取阈值


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def lcs(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i][j - 1], dp[i - 1][j])
    return dp[m][n]


def ratio(a, b):
    return lcs(a, b) / min(len(a), len(b)) if a and b else 0


def main():
    eps = sys.argv[1:] or ['P03']
    ocr = RapidOCR()
    features = np.load(os.path.join(BASE, 'face_features_insightface.npz'))
    enc = features['encodings']
    norm_known = enc / np.linalg.norm(enc, axis=1, keepdims=True)
    app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    print('加载完成', flush=True)

    report = {}
    for ep in eps:
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            continue
        data = json.load(open(os.path.join(BASE, 'subtitle_clean', f'[{ep}]'
                                           + os.path.basename(video[0]).split(']')[1].replace('.mp4', '')
                                           + '.json'), encoding='utf-8'))
        data.sort(key=lambda r: parse_ts(r.get('timestamp', '')) or 0)

        def max_sim(faces, nk):
            s = [float(np.dot(fc.normed_embedding, nk.T).max())
                 for fc in faces if np.linalg.norm(fc.embedding) > 0]
            return max(s) if s else 0.0

        def face_best(frame, nk):
            """返回 (max_sim, 该人脸的 embedding 或 None, 人脸数)"""
            faces = app.get(frame)
            if not faces:
                return 0.0, None, 0
            best = None
            for f in faces:
                if np.linalg.norm(f.embedding) <= 0:
                    continue
                s = float(np.dot(f.normed_embedding, nk.T).max())
                if best is None or s > best[0]:
                    best = (s, f.embedding.astype(np.float32))
            return (best[0], best[1], len(faces)) if best else (0.0, None, len(faces))

        # ---- 实验 A: 0.5s 步长窗口细扫 ----
        cap = cv2.VideoCapture(video[0])

        def read_at(t):
            if t < 0:
                return None
            cap.set(cv2.CAP_PROP_POS_MSEC, int(t * 1000 + 800))
            ret, frame = cap.read()
            return frame if ret else None

        n_total = n_win = 0
        n_hit05 = n_hit15 = 0     # 0.5s 命中 / 1s 步长(对照,模拟现策略)命中
        sims05 = []
        aug = []                   # 自增强锚点候选 embedding
        for i, r in enumerate(data):
            text = r.get('text', '').strip()
            sec = parse_ts(r.get('timestamp', ''))
            if not text or sec is None:
                continue
            next_sec = parse_ts(data[i + 1].get('timestamp', '')) if i + 1 < len(data) else None
            end = sec + WINDOW_MAX
            if next_sec is not None:
                end = min(end, next_sec - WINDOW_GAP)
            end = max(end, sec + 1)
            # 0.5s 步长遍历（与 1s 步长对照）
            best05 = None  # (t, sim, emb)
            best15 = None
            t = float(sec)
            while t <= end + 1e-6:
                frame = read_at(t)
                if frame is not None:
                    sim, emb, _ = face_best(frame, norm_known)
                    if best05 is None or sim > best05[1]:
                        best05 = (t, sim, emb)
                    if int(t) == t and (best15 is None or sim > best15[1]):
                        best15 = (t, sim, emb)
                t += STEP
            n_total += 1
            if best05 is not None:
                n_win += 1
                sims05.append(best05[1])
                if best05[1] >= 0.4:
                    n_hit05 += 1
                if best05[1] >= AUG_SIM_MIN and best05[2] is not None:
                    aug.append(best05[2])           # 最高相似人脸 embedding
            if best15 is not None and best15[1] >= 0.4:
                n_hit15 += 1
        cap.release()
        report[f'{ep}_A'] = {
            'total': n_total, 'win_best': n_win,
            'hit_05s': n_hit05, 'hit_05s_pct': round(n_hit05 / n_win * 100, 1) if n_win else 0,
            'hit_1s_ref': n_hit15, 'hit_1s_pct': round(n_hit15 / n_win * 100, 1) if n_win else 0,
            'aug_anchor_candidates': len(aug),
        }
        print(f'[A] {ep}: 条目 {n_total}，窗口最优 {n_win} | 0.5s 细扫命中 {n_hit05} '
              f'({n_hit05 / n_win * 100:.1f}%) vs 1s 对照 {n_hit15} ({n_hit15 / n_win * 100:.1f}%) '
              f'| 自增强候选 {len(aug)}', flush=True)

        # ---- 实验 B: 锚点自增强（用窗口最优人脸 embedding 补锚点）----
        aug_emb = np.stack(aug) if aug else np.zeros((0, 512), dtype=np.float32)
        nk_aug = np.concatenate([norm_known, aug_emb / np.linalg.norm(aug_emb, axis=1, keepdims=True)], axis=0) \
            if len(aug) else norm_known
        files = sorted([f for f in os.listdir(FRAMES_DIR)
                        if re.match(rf'^{ep}_\d+m\d+s\.jpg$', f)])
        n_base = n_augb = 0
        for f in files:
            img = cv2.imread(os.path.join(FRAMES_DIR, f))
            if img is None:
                continue
            sb, _, _ = face_best(img, norm_known)
            sa, _, _ = face_best(img, nk_aug)
            if sb >= 0.4:
                n_base += 1
            if sa >= 0.4:
                n_augb += 1
        report[f'{ep}_B'] = {
            'sel_frames': len(files),
            'hit_base': n_base, 'hit_base_pct': round(n_base / len(files) * 100, 1) if files else 0,
            'hit_aug': n_augb, 'hit_aug_pct': round(n_augb / len(files) * 100, 1) if files else 0,
            'aug_anchors_total': len(nk_aug) - 95,
        }
        print(f'[B] {ep}: 已选帧 {len(files)} | 基线锚点命中 {n_base} ({n_base / len(files) * 100:.1f}%) '
              f'vs 自增强锚点 {(len(nk_aug))} 个: {n_augb} ({n_augb / len(files) * 100:.1f}%)', flush=True)

    out = os.path.join(REVIEW_DIR, 'probe_aizen_v3.json')
    json.dump(report, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'保存: {out}')


if __name__ == '__main__':
    main()
