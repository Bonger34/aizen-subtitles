# -*- coding: utf-8 -*-
"""extract_faces_enhanced.py — 方案C：人脸优先 + 字幕兜底的全量抽帧

策略（每条字幕）：
  1. 在 ts±1 三帧中依次做字幕匹配（rapidocr LCS>=0.5 或包含）
  2. 第一帧匹配且主演 sim>=0.4 → 直接保存（最快路径，覆盖大多数）
  3. 若匹配但 sim<0.4 → 继续看下一帧，保留所有匹配候选，最终选 sim 最高的保存
  4. 三帧都无匹配 → 扩展 ts±2 两帧兜底；仍无 → 标记 ghost（不保存）
  5. 全部候选均无主演脸 → 取字幕匹配最好的帧保存（覆盖率兜底，不丢帧）
帧命名 = 实际选中帧的时刻（Pxx_XmXXs.jpg），与 make_frames_map ±1s 回退兼容。

用法: python extract_faces_enhanced.py [--ep P01]（无 --ep 全量）
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
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES_DIR = os.path.join(BASE, 'web', 'frames')
SUBTITLE_AREA = (100, 895, 1820, 985)
W, H = 960, 540
FRAME_OFFSET_MS = 800
MATCH_MIN = 0.5
FACE_SIM_MIN = 0.4        # 主演命中阈值（与旧管线一致）
FACE_RATIO_MIN = 0.0005   # 面积占比阈值


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def ts_str(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


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
    args = sys.argv[1:]
    ep_filter = args[args.index('--ep') + 1] if '--ep' in args else None

    print('加载 RapidOCR...', flush=True)
    ocr = RapidOCR()
    print('加载 InsightFace (buffalo_l)...', flush=True)
    app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    features = np.load(os.path.join(BASE, 'face_features_insightface.npz'))
    norm_known = features['encodings'] / np.linalg.norm(features['encodings'], axis=1, keepdims=True)
    print('加载完成', flush=True)

    def ocr_match(frame, text):
        crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
        result, _ = ocr(crop)
        texts = [x[1] for x in result] if result else []
        best = max((ratio(text, x) for x in texts), default=0)
        return best >= MATCH_MIN or any(text.replace(' ', '') in x.replace(' ', '') for x in texts)

    def face_score(frame):
        """返回 (best_sim, 面积占比, 人脸数)"""
        faces = app.get(frame)
        if not faces:
            return 0.0, 0.0, 0
        h, w = frame.shape[:2]
        area = h * w
        best_sim, best_ratio = 0.0, 0.0
        for f in faces:
            if np.linalg.norm(f.embedding) == 0:
                continue
            sim = float(np.dot(f.normed_embedding, norm_known.T).max())
            rect = f.bbox
            r_area = max(0.0, (rect[2] - rect[0]) * (rect[3] - rect[1])) / area
            if sim > best_sim:
                best_sim = sim
                best_ratio = r_area
        return best_sim, best_ratio, len(faces)

    total_ok = total_all = 0
    for fname in sorted(os.listdir(CLEAN_DIR)):
        if not fname.endswith('.json'):
            continue
        ep = fname.split(']')[0].lstrip('[')
        if ep_filter and ep != ep_filter:
            continue
        data = json.load(open(os.path.join(CLEAN_DIR, fname), encoding='utf-8'))
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            continue
        # 清理本集旧正式帧
        old = [f for f in os.listdir(FRAMES_DIR) if re.match(rf'^P{ep[1:]}_\d+m\d+s.*\.jpg$', f)]
        for f in old:
            os.remove(os.path.join(FRAMES_DIR, f))
        print(f'{ep}: 清理旧帧 {len(old)} 张', flush=True)

        cap = cv2.VideoCapture(video[0])
        ok_n, ghost, noface_n = 0, [], 0
        for r in data:
            text = r.get('text', '').strip()
            sec = parse_ts(r.get('timestamp', ''))
            if not text or sec is None:
                continue
            best_cand = None   # (off, sim, frame)
            saved = False
            # 第一轮：ts±1
            for off in (0, -1, 1):
                t = sec + off
                if t < 0:
                    continue
                cap.set(cv2.CAP_PROP_POS_MSEC, int(t * 1000 + FRAME_OFFSET_MS))
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue
                if not ocr_match(frame, text):
                    continue
                sim, _r, _c = face_score(frame)
                if sim >= FACE_SIM_MIN:
                    cv2.imwrite(os.path.join(FRAMES_DIR, f'{ep}_{ts_str(t)}.jpg'),
                                cv2.resize(frame, (W, H)), [cv2.IMWRITE_JPEG_QUALITY, 82])
                    ok_n += 1
                    saved = True
                    break
                if best_cand is None or sim > best_cand[1]:
                    best_cand = (off, sim, frame)
            if saved:
                continue
            # 第二轮：ts±2 兜底
            if best_cand is None:
                for off in (2, -2):
                    t = sec + off
                    if t < 0:
                        continue
                    cap.set(cv2.CAP_PROP_POS_MSEC, int(t * 1000 + FRAME_OFFSET_MS))
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        continue
                    if not ocr_match(frame, text):
                        continue
                    sim, _r, _c = face_score(frame)
                    if sim >= FACE_SIM_MIN:
                        cv2.imwrite(os.path.join(FRAMES_DIR, f'{ep}_{ts_str(t)}.jpg'),
                                    cv2.resize(frame, (W, H)), [cv2.IMWRITE_JPEG_QUALITY, 82])
                        ok_n += 1
                        saved = True
                        break
                    if best_cand is None or sim > best_cand[1]:
                        best_cand = (off, sim, frame)
            if saved:
                continue
            if best_cand is not None:
                # 有字幕匹配但无主演：取 sim 最高的候选保存（覆盖兜底，不丢帧）
                off, sim, frame = best_cand
                cv2.imwrite(os.path.join(FRAMES_DIR, f'{ep}_{ts_str(sec + off)}.jpg'),
                            cv2.resize(frame, (W, H)), [cv2.IMWRITE_JPEG_QUALITY, 82])
                ok_n += 1
                if sim < 0.1:
                    noface_n += 1
            else:
                ghost.append((r['timestamp'], text))
        cap.release()
        total_ok += ok_n
        total_all += len(data)
        print(f'{ep}: 成功 {ok_n}/{len(data)}（{ok_n/len(data)*100:.1f}%，无主演脸兜底 {noface_n}），'
              f'ghost {len(ghost)}', flush=True)
        json.dump([{'ts': t, 'text': x} for t, x in ghost],
                  open(os.path.join(BASE, 'review', f'frames_ghost_{ep}.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
    print(f'\n全量总计: {total_ok}/{total_all}（{total_ok/total_all*100:.1f}%）')


if __name__ == '__main__':
    main()
