# -*- coding: utf-8 -*-
"""extract_frames_scan4.py — 二值化预处理 + rapidocr 重扫无帧台词

突破点（P03 7m12s 实验）：反色/艺术字字幕普通预处理读不出，
灰度反色 + OTSU 二值化后 rapidocr 可正常识别。

流程：对无帧台词窗口 0.2s 步长采样 → bin 预处理 → rapidocr 识别 →
     清理引号后分行匹配（LCS>=0.5 或包含）→ 取最佳命中帧保存。
用法: python extract_frames_scan4.py
"""
import json
import os
import re
import sys

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES_DIR = os.path.join(BASE, 'web', 'frames')
FMAP_JS = os.path.join(BASE, 'Web', 'frames_map.js')
SUBTITLE_AREA = (100, 895, 1820, 985)
W, H = 960, 540
RANGE_BEFORE = 500
RANGE_AFTER = 3500
MATCH_MIN = 0.5
STEP_MS = 200

QUOTE_RE = re.compile(r'[“”‘’"\']')


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
    cleaned = QUOTE_RE.sub('', ocr_text).strip()
    ocr_lines = [x for x in re.split(r'\s+', cleaned) if len(x) >= 2] or [cleaned]
    for lib in lib_lines:
        lib_c = QUOTE_RE.sub('', lib.replace(' ', ''))
        if not lib_c:
            continue
        for ocr in ocr_lines:
            ocr_c = ocr.replace(' ', '')
            if not ocr_c:
                continue
            if ratio(lib_c, ocr_c) >= MATCH_MIN or lib_c in ocr_c or ocr_c in lib_c:
                return True
    return False


def binprep(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    inv = 255 - gray
    _, b = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.cvtColor(b, cv2.COLOR_GRAY2BGR)


def main():
    m = re.search(r'=\s*(\{.*?\})\s*;', open(FMAP_JS, encoding='utf-8').read(), re.S)
    FMAP = json.loads(m.group(1))
    print(f'已有映射 {len(FMAP)}', flush=True)
    ocr = RapidOCR()

    channels = {}
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
            best = None
            t_ms = start_ms
            while t_ms <= end_ms:
                ret, frame = cap.read()
                if frame is None:
                    break
                crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3],
                             SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
                res, _ = ocr(binprep(crop))
                otext = ''.join(x[1] for x in res) if res else ''
                if otext and match_lines(lib_lines, otext):
                    ocr_c = QUOTE_RE.sub('', otext).replace(' ', '')
                    bl = max((ratio(QUOTE_RE.sub('', l).replace(' ', ''), ocr_c)
                              for l in lib_lines if l), default=0)
                    if best is None or bl > best[0]:
                        best = (bl, frame.copy(), t_ms)
                        if bl >= 0.99:
                            break
                t_ms += STEP_MS
            if best is not None:
                name = f'{ep}_{ts_str(round(best[2] / 1000))}.jpg'
                cv2.imwrite(os.path.join(FRAMES_DIR, name),
                            cv2.resize(best[1], (W, H)), [cv2.IMWRITE_JPEG_QUALITY, 82])
                fixed.append({'ep': ep, 'ts': r.get('timestamp'), 'text': text,
                              'frame': name, 'ratio': round(best[0], 3)})
            else:
                still.append((ep, r))
        cap.release()
        print(f'{ep}: 累计命中 {len(fixed)}', flush=True)

    print(f'\n结果: bin+rapidocr 命中 {len(fixed)} | 仍未命中 {len(still)}', flush=True)
    with open(os.path.join(BASE, 'review', 'frames_scan4_fix.json'), 'w', encoding='utf-8') as fh:
        json.dump({'fixed': fixed,
                   'still': [{'ep': e, 'ts': r.get('timestamp'), 'text': r.get('text', '')[:30]}
                             for e, r in still]},
                  fh, ensure_ascii=False, indent=1)
    print('记录: review/frames_scan4_fix.json')


if __name__ == '__main__':
    main()
