# -*- coding: utf-8 -*-
"""extract_frames_scan3.py — 无帧图台词的逐帧密集扫描（第三级）

针对剩余 40 条无帧台词：
1. 逐帧扫描（40ms ≈ 25fps 每帧都查），补救 1-3 帧就结束的语气词
2. 多行分行匹配：库文本(可能含\n)与 OCR 行集合两两比对，任一 行 LCS>=0.5 或包含即命中
3. 遍历窗口取「本句最佳匹配帧」，仍严格 require 校验，无兜底（宁缺毋滥）

用法: python extract_frames_scan3.py   （约 20 分钟）
"""
import glob
import json
import os
import re

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES_DIR = os.path.join(BASE, 'web', 'frames')
FMAP_JS = os.path.join(BASE, 'docs', 'frames_map.js')
SUBTITLE_AREA = (100, 895, 1820, 985)
W, H = 960, 540
RANGE_BEFORE = 500      # ms
RANGE_AFTER = 3500
MATCH_MIN = 0.5
FPS = 25.0


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


def match_lines(lib_lines, ocr_text):
    """分行匹配：库文本任一行与 OCR 整体/任一子句 LCS>=0.5 或包含。"""
    ocr_lines = [x for x in re.split(r'[\s]+', ocr_text.strip()) if len(x) >= 2] or [ocr_text.strip()]
    for lib in lib_lines:
        lib_c = lib.replace(' ', '')
        if not lib_c:
            continue
        for ocr in ocr_lines:
            ocr_c = ocr.replace(' ', '')
            if not ocr_c:
                continue
            if (ratio(lib_c, ocr_c) >= MATCH_MIN
                    or lib_c in ocr_c or ocr_c in lib_c):
                return True
    return False


def main():
    m = re.search(r'=\s*(\{.*?\})\s*;', open(FMAP_JS, encoding='utf-8').read(), re.S)
    FMAP = json.loads(m.group(1))
    print(f'已有映射 {len(FMAP)}', flush=True)

    ocr = RapidOCR()
    # 收集无映射条目
    channels = {}  # ep -> (video, data, missing)
    for fname in sorted(os.listdir(CLEAN_DIR)):
        if not fname.endswith('.json'):
            continue
        ep = fname.split(']')[0].lstrip('[')
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            continue
        data = json.load(open(os.path.join(CLEAN_DIR, fname), encoding='utf-8'))
        missing = [r for r in data if f'{fname[:-5]}|{r.get("timestamp", "")}' not in FMAP]
        if missing:
            channels[ep] = (video[0], missing)
    total = sum(len(v[1]) for v in channels.values())
    print(f'待扫 {total} 条', flush=True)

    fixed, still = [], []
    for ep, (video, missing) in channels.items():
        cap = cv2.VideoCapture(video)
        for r in missing:
            text = r.get('text', '').strip()
            sec = parse_ts(r.get('timestamp', ''))
            if not text or sec is None:
                still.append((ep, r))
                continue
            lib_lines = text.split('\n')
            start_ms = sec * 1000 - RANGE_BEFORE
            end_ms = sec * 1000 + RANGE_AFTER
            cap.set(cv2.CAP_PROP_POS_MSEC, int(start_ms))
            best = None     # (ratio, frame, ms)
            t_ms = start_ms
            n_frames = int((end_ms - start_ms) / 1000 * FPS)
            for _ in range(n_frames):
                ret, frame = cap.read()
                if frame is None:
                    break
                crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3],
                             SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
                res, _ = ocr(crop)
                otext = ''.join(x[1] for x in res) if res else ''
                if otext and match_lines(lib_lines, otext):
                    # 综合最好：取与库文本最大 LCS 比的帧
                    ocr_c = otext.replace(' ', '')
                    best_line = max((ratio(l.replace(' ', ''), ocr_c) for l in lib_lines if l), default=0)
                    if best is None or best_line > best[0]:
                        best = (best_line, frame.copy(), t_ms)
                        if best_line >= 0.99:
                            break
                t_ms += int(1000 / FPS)
            if best is not None:
                name = f'{ep}_{ts_str(round(best[2] / 1000))}.jpg'
                cv2.imwrite(os.path.join(FRAMES_DIR, name),
                            cv2.resize(best[1], (W, H)), [cv2.IMWRITE_JPEG_QUALITY, 82])
                fixed.append({'ep': ep, 'ts': r.get('timestamp'), 'text': text,
                              'frame': name, 'ratio': round(best[0], 3)})
            else:
                still.append((ep, r))
        cap.release()
        print(f'{ep}: 完成（累计命中 {len(fixed)}）', flush=True)

    print(f'\n结果: 命中 {len(fixed)} | 仍未命中 {len(still)}')
    with open(os.path.join(BASE, 'review', 'frames_scan3_fix.json'), 'w', encoding='utf-8') as fh:
        json.dump({'fixed': fixed,
                   'still': [{'ep': e, 'ts': r.get('timestamp'), 'text': r.get('text', '')[:30]}
                             for e, r in still]},
                  fh, ensure_ascii=False, indent=1)
    print('记录: review/frames_scan3_fix.json')


if __name__ == '__main__':
    main()
