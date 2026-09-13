# -*- coding: utf-8 -*-
"""q_locate_frame.py — 在视频中定位"已存帧图"的真实时刻。

背景: make_frames_full.py 用 cap.set(CAP_PROP_POS_MSEC) 抽帧(该 API 实测不可靠), 抽到哪一帧
就存成 ts-1/ts/ts+1 中的任一帧, 但文件名始终用库时间戳 ts —— 所以帧图命名时刻 ≠ 画面真实时刻。
本脚本用下采样灰度模板匹配, 在 [ts-R, ts+R] 内找出帧图的真实位置, 用于量化偏移分布。
用法: python q_locate_frame.py P02 0m08s 0m19s 0m26s [R秒, 默认30]
"""
import json
import os
import re
import sys

import cv2
import numpy as np

B = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(B, 'Videos')
FR = os.path.join(B, 'Web', 'frames')
SZ = (64, 36)


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def thumb(img):
    g = cv2.cvtColor(cv2.resize(img, SZ, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    return g.astype(np.float32)


def main():
    ep = sys.argv[1]
    args = [a for a in sys.argv[2:] if not a.isdigit()]
    R = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 30
    s = open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read()
    MAP = json.loads(s[s.index('{'):s.rindex('}') + 1])
    title = next(t for t in MAP if t.startswith(f'[{ep}]')).split('|')[0]
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)

    targets = []
    for ts in args:
        sec = parse_ts(ts)
        ref = cv2.imread(os.path.join(FR, MAP[f'{title}|{ts}']))
        if ref is None:
            print(f'{ts}: 帧图缺失')
            continue
        targets.append({'ts': ts, 'sec': sec, 'ref': thumb(ref),
                        'lo': max(0, int((sec - R) * fps)), 'hi': int((sec + R) * fps)})
    print(f'定位 {len(targets)} 个帧图, 搜索半径 {R}s, fps={fps:.3f}')

    n, cur = 0, 0
    lo_all = min(t['lo'] for t in targets)
    while n < lo_all:
        cap.grab()
        n += 1
    rows = []
    while any(t['lo'] <= n <= t['hi'] for t in targets) and n < int(2 * 3600 * fps):
        ok, f = cap.grab(), None
        if not ok:
            break
        ok, f = cap.retrieve()
        if not ok:
            break
        th = thumb(f)
        for t in targets:
            if t['lo'] <= n <= t['hi']:
                d = float(np.abs(th - t['ref']).mean())
                t.setdefault('best', (1e9, -1))
                if d < t['best'][0]:
                    t['best'] = (d, n)
        n += 1
    cap.release()
    for t in targets:
        if 'best' not in t:
            print(f"{t['ts']}: 未搜索(超出范围)")
            continue
        d, fno = t['best']
        real = fno / fps
        print(f"{t['ts']} (={t['sec']}s): 真实位置 {int(real) // 60}m{int(real) % 60:02d}s "
              f"(第{fno}帧) 偏移 {real - t['sec']:+.2f}s MAE={d:.1f}")
        rows.append({'ts': t['ts'], 'sec': t['sec'], 'real_sec': round(real, 2),
                     'offset': round(real - t['sec'], 2), 'mae': round(d, 1)})
    json.dump(rows, open(os.path.join(B, 'review', 'q_locate_frame.json'), 'w',
                         encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
