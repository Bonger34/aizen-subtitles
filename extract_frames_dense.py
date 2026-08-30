# -*- coding: utf-8 -*-
"""extract_frames_dense.py — 密集扫描补齐无帧图台词

背景：字幕提取是 0.2~0.4s 密集采样，帧图抽取是 1s 步长采样；
显示 <1s 的短句在秒级采样下会被错过（OCR 校验失败 → 无帧）。
本脚本只对「无帧映射」的台词做 0.2s 步长密集扫描，精准补齐缺口。

逻辑（与窗口版一致 + 更高采样密度）：
1. 读 frames_map.js 得到已有帧映射 key（f|ts）集合
2. 遍历 subtitle_clean 所有条目，找出无映射者（缺口）
3. 对每条在 [ts-0.5s, ts+3s] 以 0.2s 步长采样；OCR 校验（LCS>=0.5 或包含）
   命中帧保存（960x540，帧名=实际时刻）
4. 无命中 → 兜底：取窗口内「存在任意字幕文本」的帧保存
5. 输出审查记录 review/frames_dense_fix.json

用法: python extract_frames_dense.py [--ep P02]（默认全部缺口集；约 20-40 分钟）
"""
import glob
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
STEP_MS = 200          # 密集采样步长（毫秒）
RANGE_BEFORE = 500     # ts 之前扫描量（毫秒）
RANGE_AFTER = 3000     # ts 之后扫描上限（毫秒）
MATCH_MIN = 0.5


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


def load_fmap():
    m = re.search(r'=\s*(\{.*?\})\s*;', open(FMAP_JS, encoding='utf-8').read(), re.S)
    return json.loads(m.group(1)) if m else {}


def main():
    args = sys.argv[1:]
    ep_filter = args[args.index('--ep') + 1] if '--ep' in args else None
    fmap = load_fmap()
    print(f'已有帧映射: {len(fmap)}', flush=True)

    ocr = RapidOCR()
    print('OCR 就绪', flush=True)

    # 收集缺口条目
    pending = {}   # ep -> [(video, [items])]
    for fname in sorted(os.listdir(CLEAN_DIR)):
        if not fname.endswith('.json'):
            continue
        ep = fname.split(']')[0].lstrip('[')
        if ep_filter and ep != ep_filter:
            continue
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            continue
        data = json.load(open(os.path.join(CLEAN_DIR, fname), encoding='utf-8'))
        data.sort(key=lambda r: parse_ts(r.get('timestamp', '')) or 0)
        miss = []
        for i, r in enumerate(data):
            key = f'{fname[:-5]}|{r.get("timestamp", "")}'
            if key not in fmap:
                miss.append((i, r))
        if miss:
            pending[ep] = (video[0], data, miss)
        print(f'{ep}: 缺口 {len(miss)} 条', flush=True)

    total = sum(len(v[2]) for v in pending.values())
    print(f'总缺口 {total} 条', flush=True)

    stats = {'matched': 0, 'fallback_any_sub': 0, 'still_miss': 0}
    fix_log = []
    for ep, (video, data, miss) in pending.items():
        cap = cv2.VideoCapture(video)
        for i, r in miss:
            text = r.get('text', '').strip()
            sec = parse_ts(r.get('timestamp', ''))
            if not text or sec is None:
                stats['still_miss'] += 1
                continue
            # 窗口：[sec-0.5, sec+3]（上一句留给下一条处理，不越 ts-0.5 太多）
            start_ms = sec * 1000 - RANGE_BEFORE
            end_ms = sec * 1000 + RANGE_AFTER
            best_sub = None   # (t_ms, sim) 任意字幕文本帧（兜底）
            best_match = None # (t_ms, sim) 本句匹配帧
            t_ms = start_ms
            while t_ms <= end_ms:
                cap.set(cv2.CAP_PROP_POS_MSEC, int(t_ms))
                ret, frame = cap.read()
                if frame is not None:
                    crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3],
                                 SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
                    res, _ = ocr(crop)
                    otext = ''.join(x[1] for x in res) if res else ''
                    if otext:
                        # 任意字幕文本：兜底候选取最近 moment 的（优先 ts 后第一帧）
                        if best_sub is None:
                            best_sub = (t_ms, 0.0)
                    if otext and (ratio(text, otext) >= MATCH_MIN
                                  or text.replace(' ', '') in otext.replace(' ', '')):
                        if best_match is None:
                            best_match = (t_ms, ratio(text, otext))
                            break   # 已找到本句字幕，停止（显示窗口内第一帧即可）
                t_ms += STEP_MS
            save_ms, saved = None, False
            if best_match is not None:
                save_ms = best_match[0]
                stats['matched'] += 1
                saved = True
            elif best_sub is not None:
                # 兜底：ts 之后最近的「有字幕」帧（画面大概是相邻句）
                save_ms = best_sub[0]
                stats['fallback_any_sub'] += 1
                saved = True
            if not saved:
                stats['still_miss'] += 1
                fix_log.append({'ep': ep, 'ts': r.get('timestamp'), 'text': text, 'why': 'none'})
                continue
            cap.set(cv2.CAP_PROP_POS_MSEC, int(save_ms))
            ret, frame = cap.read()
            if frame is None:
                stats['still_miss'] += 1
                continue
            name = f'{ep}_{ts_str(round(save_ms / 1000))}.jpg'
            cv2.imwrite(os.path.join(FRAMES_DIR, name),
                        cv2.resize(frame, (W, H)), [cv2.IMWRITE_JPEG_QUALITY, 82])
            fix_log.append({'ep': ep, 'ts': r.get('timestamp'), 'text': text,
                            'frame': name, 'ms': save_ms,
                            'kind': 'match' if best_match is not None else 'fallback'})
        cap.release()
        print(f'{ep}: 补齐完成（累计 {stats["matched"]} 命中 / {stats["fallback_any_sub"]} 兜底）',
              flush=True)

    rate = (stats['matched'] + stats['fallback_any_sub']) / total * 100 if total else 0
    print(f'\n统计: 总缺口 {total} | 本句命中 {stats["matched"]} | 兜底 {stats["fallback_any_sub"]} '
          f'| 未补 {stats["still_miss"]} | 补齐率 {rate:.1f}%')
    with open(os.path.join(BASE, 'review', 'frames_dense_fix.json'), 'w', encoding='utf-8') as fh:
        json.dump(fix_log, fh, ensure_ascii=False, indent=2)
    print(f'审查记录: review/frames_dense_fix.json')


if __name__ == '__main__':
    main()
