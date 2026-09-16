# -*- coding: utf-8 -*-
"""q_seektest.py — 验证"seek(ts+Δ) + 与已存帧图做内容校验"能否稳定拿到帧图对应的 1080p 原帧。

动机: 顺序解码全片两遍约需 1 小时; 若 seek 命中率高, 定位成本可降到几分钟(校验用下采样灰度 MAE)。
用法: python q_seektest.py P02 [条数, 默认40]
输出: review/q_seektest.json + 控制台统计
"""
import json
import os
import re
import sys
import time

import cv2
import numpy as np

B = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(B, 'Videos')
FR = os.path.join(B, 'docs', 'frames')
CLEAN = os.path.join(B, 'subtitle_clean')
SZ = (64, 36)
CANDS = (-0.8, -1.8, -2.8, -3.8, 0.2, -0.3, -1.3, -2.3)


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def thumb(img):
    return cv2.cvtColor(cv2.resize(img, SZ, interpolation=cv2.INTER_AREA),
                        cv2.COLOR_BGR2GRAY).astype(np.float32)


def main():
    ep = sys.argv[1]
    n_max = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 40
    s = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
    MAP = json.loads(s[s.index('{'):s.rindex('}') + 1])
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]
    title = fn[:-5]
    data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))[:n_max]
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)

    hit1 = hitany = 0
    t_seek = 0.0
    rows = []
    for e in data:
        ts, sec = e['timestamp'], parse_ts(e['timestamp'])
        f = MAP.get(f'{title}|{ts}')
        ref_img = cv2.imread(os.path.join(FR, f)) if f else None
        if ref_img is None or sec is None:
            continue
        ref = thumb(ref_img)
        found, best = None, (1e9, None)
        for k, off in enumerate(CANDS):
            t = max(0.0, sec + off)
            ta = time.time()
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, fr = cap.read()
            t_seek += time.time() - ta
            if not ok:
                continue
            d = float(np.abs(thumb(fr) - ref).mean())
            if d < best[0]:
                best = (d, off)
            if d < 6.0:
                found = off
                break
        if found is not None:
            hitany += 1
            if found == CANDS[0]:
                hit1 += 1
        rows.append({'ts': ts, 'found': found, 'best_off': best[1], 'best_mae': round(best[0], 2)})
        print(f"  {ts:>7s} 命中={found} 最佳偏移={best[1]} MAE={best[0]:.1f}")
    cap.release()
    n = len(rows)
    print(f'\n{n} 条: 首次候选(-0.8s)命中 {hit1} ({hit1 * 100.0 / max(1, n):.0f}%), '
          f'多候选命中 {hitany} ({hitany * 100.0 / max(1, n):.0f}%)')
    print(f'平均每次 seek+read {t_seek / max(1, n * 3) * 1000:.0f}ms(按每条约3次估计)')
    json.dump(rows, open(os.path.join(B, 'review', 'q_seektest.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
