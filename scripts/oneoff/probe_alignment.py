# -*- coding: utf-8 -*-
"""probe_alignment.py — 对"无文本"删除项做时间对齐探查

思路：用户复核发现部分条目 ts 与画面字幕错位（ts 处画面显示的是相邻句/无字幕）。
对每条删除项：在 ts-3s..ts+3s 逐秒抽取帧，OCR 字幕区，找与"原库文本"最匹配的时刻，
输出候选（k/s 偏移 + 该帧实际 OCR 文本），并把最佳帧的字幕区放大图存盘供人眼确认。

用法: python probe_alignment.py
"""
import glob
import json
import os
import re

import cv2
from rapidocr_onnxruntime import RapidOCR

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
BACKUP_DIR = os.path.join(BASE, 'archive', 'datasets', 'subtitle_clean_prereview')  # 修正前快照
FIXES = os.path.join(BASE, 'review', 'user_fixes.json')
VIDEO_DIR = os.path.join(BASE, 'Videos')
OUT_DIR = os.path.join(BASE, 'review', 'probe_alignment')
SUBTITLE_AREA = (100, 895, 1820, 985)  # 与管线一致
OFFSETS = range(-3, 4)  # ts±3s 逐秒
MATCH_MIN = 0.3         # LCS 阈值：低于此视为未找到

EP_RE = re.compile(r'^\[(P\d{2})\]')


def lcs_ratio(a, b):
    if not a or not b:
        return 0
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i][j - 1], dp[i - 1][j])
    return dp[m][n] / m


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def main():
    with open(FIXES, encoding='utf-8') as f:
        fixes = json.load(f)
    fixes.pop('_meta', None)

    # 收集删除项及其修正前原文
    items = []
    for ep, pairs in fixes.items():
        for ts, fx in pairs.items():
            if fx['action'] == 'remove':
                items.append((ep, ts))
    print(f'待探查删除项: {len(items)} 条')

    ocr = RapidOCR()
    os.makedirs(OUT_DIR, exist_ok=True)
    report = []
    for ep, ts in items:
        sec = parse_ts(ts)
        # 修正前旧文本（来自备份快照；注意 glob 会把 [P01] 当字符类，改用 listdir 匹配）
        old_text = ''
        for fname in sorted(os.listdir(BACKUP_DIR)):
            if fname.startswith(f'[{ep}]') and fname.endswith('.json'):
                for r in json.load(open(os.path.join(BACKUP_DIR, fname), encoding='utf-8')):
                    if r.get('timestamp') == ts:
                        old_text = r.get('text', '')
        # 视频路径（listdir 方式，避免 glob 字符类歧义）
        video = ''
        for fname in sorted(os.listdir(VIDEO_DIR)):
            if fname.startswith(f'[{ep}]') and fname.lower().endswith(('.mp4', '.mkv')):
                video = os.path.join(VIDEO_DIR, fname)
                break
        best = (0, '', None, None)  # (score, ocr_text, offset, img)
        rows = []
        cap = cv2.VideoCapture(video)
        for off in OFFSETS:
            cap.set(cv2.CAP_PROP_POS_MSEC, (sec + off) * 1000 + 800)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
            result, _ = ocr(np_require(crop))
            texts = [r[1] for r in result] if result else []
            joined = ' '.join(texts)
            score = max((lcs_ratio(old_text, t) for t in texts), default=0)
            rows.append((off, joined, score, texts))
            if score > best[0]:
                best = (score, joined, off, texts)
        cap.release()
        hit = best[0] >= MATCH_MIN
        off_disp = best[2] if best[2] is not None else 0
        print(f'{ep} {ts} 原=[{old_text[:30]}] '
              f'{"命中" if hit else "未找到"} 最佳={best[0]:.2f}@{off_disp:+d}s 帧OCR=[{best[1][:40]}]')
        for off, joined, score, _t in rows:
            print(f'    {off:+d}s : {score:.2f}  [{joined[:50]}]')
        # 保存最佳命中帧的字幕区放大图（2x）
        if hit and best[2] is not None:
            cap = cv2.VideoCapture(video)
            cap.set(cv2.CAP_PROP_POS_MSEC, (sec + best[2]) * 1000 + 800)
            _ok, frame = cap.read()
            cap.release()
            if frame is not None:
                crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
                crop = cv2.resize(crop, (crop.shape[1] * 2, crop.shape[0] * 2), interpolation=cv2.INTER_CUBIC)
                out = os.path.join(OUT_DIR, f'{ep}_{ts}_off{best[2]:+d}.jpg')
                cv2.imwrite(out, crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
                report.append({'ep': ep, 'ts': ts, 'offset': best[2], 'score': round(best[0], 2),
                               'frame_ocr': best[1], 'old_text': old_text, 'img': out})
    with open(os.path.join(OUT_DIR, 'report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n输出: {OUT_DIR}（命中 {len(report)}/{len(items)}）')


def np_require(img):
    """cv2 帧转 numpy（rapidocr 直接接受）"""
    return img


if __name__ == '__main__':
    main()
