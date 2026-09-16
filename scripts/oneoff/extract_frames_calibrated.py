# -*- coding: utf-8 -*-
"""extract_frames_calibrated.py — 试点：对一集（ts 校准后）重抽帧并验证命中率

逻辑：读 subtitle_clean/[EP].json（校准后 ts），每条按 ts 优先、ts±1 兜底，
rapidocr 字幕匹配（LCS>=0.5 或包含）成功 → 保存 docs/frames/P01_XmXXs.jpg
（文件名秒 = 实际匹配帧的时刻，与 make_frames_map 的 FRAME_PATTERN 兼容）。
执行前会先删除该集旧正式帧（旧 ts 帧已失效）。

用法: python extract_frames_calibrated.py --ep P01
"""
import json
import os
import re
import sys

import cv2
from rapidocr_onnxruntime import RapidOCR

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES_DIR = os.path.join(BASE, 'docs', 'frames')
SUBTITLE_AREA = (100, 895, 1820, 985)
W, H = 960, 540
FRAME_OFFSET_MS = 800
OFFSETS = (0, -1, 1)  # 校准后 ts 优先
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


def main():
    args = sys.argv[1:]
    ep_filter = args[args.index('--ep') + 1] if '--ep' in args else None
    ocr = RapidOCR()
    total_ok = total_all = 0
    for fn in sorted(os.listdir(CLEAN_DIR)):
        if not fn.endswith('.json'):
            continue
        ep = fn.split(']')[0].lstrip('[')
        if ep_filter and ep != ep_filter:
            continue
        data = json.load(open(os.path.join(CLEAN_DIR, fn), encoding='utf-8'))
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            print(f'{ep}: 未找到视频，跳过')
            continue
        # 清旧正式帧（仅本集）
        old = [f for f in os.listdir(FRAMES_DIR) if re.match(rf'^P{ep[1:]}_\d+m\d+s.*\.jpg$', f)]
        for f in old:
            os.remove(os.path.join(FRAMES_DIR, f))
        print(f'{ep}: 清理旧正式帧 {len(old)} 张')

        cap = cv2.VideoCapture(video[0])
        ok_n = 0
        ghost = []
        for r in data:
            text = r.get('text', '').strip()
            sec = parse_ts(r.get('timestamp', ''))
            if not text or sec is None:
                continue
            saved = False
            for off in OFFSETS:
                t = sec + off
                if t < 0:
                    continue
                cap.set(cv2.CAP_PROP_POS_MSEC, int(t * 1000 + FRAME_OFFSET_MS))
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue
                crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
                result, _ = ocr(crop)
                texts = [x[1] for x in result] if result else []
                best = max((ratio(text, x) for x in texts), default=0)
                if best >= MATCH_MIN or any(text.replace(' ', '') in x.replace(' ', '') for x in texts):
                    small = cv2.resize(frame, (W, H))
                    fname = f'{ep}_{ts_str(t)}.jpg'
                    cv2.imwrite(os.path.join(FRAMES_DIR, fname), small, [cv2.IMWRITE_JPEG_QUALITY, 82])
                    ok_n += 1
                    saved = True
                    break
            if not saved:
                ghost.append((r['timestamp'], text))
        cap.release()
        total_ok += ok_n
        total_all += len(data)
        print(f'{ep}: 匹配成功 {ok_n}/{len(data)}（{ok_n/len(data)*100:.1f}%），未匹配 {len(ghost)} 条')
        for t, x in ghost[:8]:
            print(f'   未匹配 {t}「{x[:28]}」')
        json.dump([{'ts': t, 'text': x} for t, x in ghost],
                  open(os.path.join(BASE, 'review', f'frames_ghost_{ep}.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
    print(f'\n全量总计: {total_ok}/{total_all}（{total_ok/total_all*100:.1f}%）')


if __name__ == '__main__':
    main()
