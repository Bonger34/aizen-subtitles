# -*- coding: utf-8 -*-
"""extract_frames_scan3_v5.py — 剩余无帧台词的 VL 精扫（修正版）

两段式（控制成本）：
1. rapidocr 粗扫窗口（0.16s 步长）：收集「检测到任意中文字幕」的候选帧（最多 16 帧）
2. VL（PaddleOCR-VL-1.6，与字幕提取同源高精度引擎）逐候选帧识别 +
   分行匹配（LCS>=0.5 或包含），命中即保存 best 帧；仍无命中 → 保持空缺（宁缺毋滥）

用法:
  python extract_frames_scan3_v5.py --test   # 先测 P03 7m12s
  python extract_frames_scan3_v5.py          # 全量
"""
import glob
import json
import os
import re
import sys

import cv2
import numpy as np

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES_DIR = os.path.join(BASE, 'web', 'frames')
FMAP_JS = os.path.join(BASE, 'docs', 'frames_map.js')
SUBTITLE_AREA = (100, 895, 1820, 985)
W, H = 960, 540
RANGE_BEFORE = 500
RANGE_AFTER = 3500
MATCH_MIN = 0.5
FPS = 25.0
CAND_MAX = 16

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
import vl_recheck_new  # 复用 VL 管道与 vl_ocr_frame


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
    ocr_lines = [x for x in re.split(r'[\s]+', ocr_text.strip()) if len(x) >= 2] or [ocr_text.strip()]
    for lib in lib_lines:
        lib_c = lib.replace(' ', '')
        if not lib_c:
            continue
        for ocr in ocr_lines:
            ocr_c = ocr.replace(' ', '')
            if not ocr_c:
                continue
            if ratio(lib_c, ocr_c) >= MATCH_MIN or lib_c in ocr_c or ocr_c in lib_c:
                return True
    return False


def load_missing():
    m = re.search(r'=\s*(\{.*?\})\s*;', open(FMAP_JS, encoding='utf-8').read(), re.S)
    FMAP = json.loads(m.group(1))
    out = {}
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
            out[ep] = (video[0], missing)
    return out


def main():
    from rapidocr_onnxruntime import RapidOCR
    fast = RapidOCR()
    print('rapidocr 就绪', flush=True)
    test = '--test' in sys.argv
    channels = load_missing()
    if test:
        ep = 'P03'
        video, missing = channels[ep]
        missing = [r for r in missing if r.get('timestamp') == '7m12s']
        channels = {ep: (video, missing)}
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
            # 阶段1: rapidocr 粗筛候选帧（有中文字幕文本）
            cands = []   # (frame_copy, t_ms, text)
            t_ms = start_ms
            n_frames = int((end_ms - start_ms) / 1000 * FPS)
            for _ in range(n_frames):
                ret, frame = cap.read()
                if frame is None:
                    break
                if len(cands) >= CAND_MAX:
                    break
                crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3],
                             SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
                res, _ = fast(crop)
                otext = ''.join(x[1] for x in res) if res else ''
                if len(otext) >= 2:
                    cands.append((frame, t_ms, otext))
                t_ms += int(1000 / FPS)
            # 阶段2: VL 精判候选帧
            best = None
            for frame, tm, _ot in cands:
                vtext = vl_recheck_new.vl_ocr_frame(frame)
                if not vtext or not match_lines(lib_lines, vtext):
                    continue
                ocr_c = vtext.replace(' ', '')
                bl = max((ratio(l.replace(' ', ''), ocr_c) for l in lib_lines if l), default=0)
                if best is None or bl > best[0]:
                    best = (bl, frame, tm)
                    if bl >= 0.99:
                        break
            if best is not None:
                name = f'{ep}_{ts_str(round(best[2] / 1000))}.jpg'
                cv2.imwrite(os.path.join(FRAMES_DIR, name),
                            cv2.resize(best[1], (W, H)), [cv2.IMWRITE_JPEG_QUALITY, 82])
                fixed.append({'ep': ep, 'ts': r.get('timestamp'), 'text': text,
                              'frame': name, 'ratio': round(best[0], 3)})
                if test:
                    print(f'[test] 命中 {ep} {r.get("timestamp")} -> {name} '
                          f'ratio {best[0]:.2f} ({text[:18]})', flush=True)
            else:
                still.append((ep, r))
                if test:
                    print(f'[test] 未命中 {ep} {r.get("timestamp")} ({text[:18]}) '
                          f'候选 {len(cands)} 帧', flush=True)
        cap.release()
        print(f'{ep}: 完成（累计命中 {len(fixed)}）', flush=True)

    print(f'\n结果: 命中 {len(fixed)} | 仍未命中 {len(still)}', flush=True)
    with open(os.path.join(BASE, 'review', 'frames_scan3_v5_fix.json'), 'w', encoding='utf-8') as fh:
        json.dump({'fixed': fixed,
                   'still': [{'ep': e, 'ts': r.get('timestamp'), 'text': r.get('text', '')[:30]}
                             for e, r in still]},
                  fh, ensure_ascii=False, indent=1)
    print('记录: review/frames_scan3_v5_fix.json')


if __name__ == '__main__':
    main()
