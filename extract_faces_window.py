# -*- coding: utf-8 -*-
"""extract_faces_window.py — 方案E：字幕持续窗口内的人脸最优帧

针对用户需求：同一字幕（长句）持续显示 ~2-3 秒 = 连续多帧；
在同一条字幕的显示窗口内（本条 ts 起，到「下一条字幕 ts - 1s」或最多 +3s）
逐秒遍历，OCR 确认仍是本条字幕 → 取主演 sim 最高的一帧保存。
若窗口内无匹配帧 → 回退原 ts±1/±2 字幕匹配策略（保覆盖率）。

帧名 = 实际选中帧时刻（仍在台词显示窗口内，时间零漂移）。

用法: python extract_faces_window.py [--ep P01]
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
FACE_SIM_MIN = 0.4
WINDOW_MAX = 3      # 窗口上限（秒）
WINDOW_GAP = 1      # 与下一条字幕至少留 1s


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
    # 优先使用增强锚点（95 基锚点 + 全 25 集高置信爱染诚 embedding），不存在则回退原锚点
    aug_path = os.path.join(BASE, 'face_features_aisome_aug.npz')
    anchor_path = aug_path if os.path.exists(aug_path) else os.path.join(BASE, 'face_features_insightface.npz')
    features = np.load(anchor_path)
    norm_known = features['encodings'] / np.linalg.norm(features['encodings'], axis=1, keepdims=True)
    print(f'锚点文件: {os.path.basename(anchor_path)}，共 {len(norm_known)} 条', flush=True)
    print('加载完成', flush=True)

    def ocr_match(frame, text):
        crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
        result, _ = ocr(crop)
        texts = [x[1] for x in result] if result else []
        best = max((ratio(text, x) for x in texts), default=0)
        return best >= MATCH_MIN or any(text.replace(' ', '') in x.replace(' ', '') for x in texts)

    def face_score(frame):
        faces = app.get(frame)
        if not faces:
            return 0.0, 0
        sims = [float(np.dot(fc.normed_embedding, norm_known.T).max())
                for fc in faces if np.linalg.norm(fc.embedding) > 0]
        return (max(sims), len(faces)) if sims else (0.0, len(faces))

    def save(frame, ep, t):
        cv2.imwrite(os.path.join(FRAMES_DIR, f'{ep}_{ts_str(t)}.jpg'),
                    cv2.resize(frame, (W, H)), [cv2.IMWRITE_JPEG_QUALITY, 82])

    def read_at(cap, t):
        if t < 0:
            return None
        cap.set(cv2.CAP_PROP_POS_MSEC, int(t * 1000 + FRAME_OFFSET_MS))
        ret, frame = cap.read()
        return frame if ret else None

    total_ok = total_all = n_window_best = n_fallback = 0
    for fname in sorted(os.listdir(CLEAN_DIR)):
        if not fname.endswith('.json'):
            continue
        ep = fname.split(']')[0].lstrip('[')
        if ep_filter and ep != ep_filter:
            continue
        data = json.load(open(os.path.join(CLEAN_DIR, fname), encoding='utf-8'))
        data.sort(key=lambda r: parse_ts(r.get('timestamp', '')) or 0)
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            continue
        old = [f for f in os.listdir(FRAMES_DIR) if re.match(rf'^P{ep[1:]}_\d+m\d+s.*\.jpg$', f)]
        for f in old:
            os.remove(os.path.join(FRAMES_DIR, f))
        print(f'{ep}: 清理旧帧 {len(old)} 张', flush=True)

        cap = cv2.VideoCapture(video[0])
        ok_n, ghost, win_n, fb_n = 0, [], 0, 0
        for i, r in enumerate(data):
            text = r.get('text', '').strip()
            sec = parse_ts(r.get('timestamp', ''))
            if not text or sec is None:
                continue
            # 本句显示窗口：[sec, next_sec-1] 内，上限 sec+WINDOW_MAX
            next_sec = parse_ts(data[i + 1].get('timestamp', '')) if i + 1 < len(data) else None
            end = sec + WINDOW_MAX
            if next_sec is not None:
                end = min(end, next_sec - WINDOW_GAP)
            end = max(end, sec + 1)  # 至少 1 帧
            best_c = None  # (t, sim, frame)
            saved = False
            # 遍历整个窗口，收集所有「字幕仍匹配」的帧，最后取 sim 最高者（保证是持续期间最清晰一帧）
            for t in range(sec, end + 1):
                frame = read_at(cap, t)
                if frame is None:
                    continue
                if not ocr_match(frame, text):
                    continue
                sim, _n = face_score(frame)
                if best_c is None or sim > best_c[1]:
                    best_c = (t, sim, frame)
            if best_c is not None and best_c[1] >= FACE_SIM_MIN:
                save(best_c[2], ep, best_c[0])
                ok_n += 1
                win_n += 1
                saved = True
            elif best_c is not None:
                # 窗口内有字幕帧但无主演：取 sim 最高的（时间零漂移）
                save(best_c[2], ep, best_c[0])
                ok_n += 1
                win_n += 1
                saved = True
            if not saved:
                # 回退：ts→±1→±2 首次匹配即存（覆盖率兜底）
                for off in (0, -1, 1, 2, -2):
                    t = sec + off
                    frame = read_at(cap, t)
                    if frame is None:
                        continue
                    if ocr_match(frame, text):
                        save(frame, ep, t)
                        ok_n += 1
                        fb_n += 1
                        saved = True
                        break
            if not saved:
                ghost.append((r['timestamp'], text))
        cap.release()
        total_ok += ok_n
        total_all += len(data)
        n_window_best += win_n
        n_fallback += fb_n
        print(f'{ep}: 成功 {ok_n}/{len(data)}（窗口最优 {win_n}，回退 {fb_n}），ghost {len(ghost)}', flush=True)
        json.dump([{'ts': t, 'text': x} for t, x in ghost],
                  open(os.path.join(BASE, 'review', f'frames_ghost_{ep}.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
    print(f'\n全量: {total_ok}/{total_all}（{total_ok/total_all*100:.1f}%），'
          f'窗口人脸最优 {n_window_best}，回退 {n_fallback}')


if __name__ == '__main__':
    main()
