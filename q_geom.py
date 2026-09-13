# -*- coding: utf-8 -*-
"""q_geom.py — 纯几何侦察(不 OCR): 统计每帧底部文字行的位置/数量分布。

目的: 决定重 OCR 的裁剪策略 —— 固定窄带 895~985 到底切掉了多少字幕行。
输出: review/q_geom.txt, review/q_geom.json
"""
import json
import os
import re
from collections import Counter

import cv2

from q_common import split_lines, gray_white, SCAN_TOP, SCAN_BOT

B = os.path.dirname(os.path.abspath(__file__))
FR = os.path.join(B, 'Web', 'frames')
CLEAN = os.path.join(B, 'subtitle_clean')
BAND = (895, 985)          # 原窄带下缘/上缘
TAIL_START = 21 * 60 + 30  # 片尾段起点(保守)


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def main():
    MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                               open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read(),
                               re.S).group(1))
    titles = {}
    for fn in sorted(os.listdir(CLEAN)):
        if fn.endswith('.json'):
            titles[fn[:-5]] = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))

    n_frame = n_line1 = n_line2 = 0
    bottom_hist, top_hist = Counter(), Counter()
    cut_by_band = 0        # 有文字行被 985 切断
    below_only = 0         # 文字行完全在 985 以下
    multi = []             # 多文字行的帧
    tail_entries = op_entries = 0
    entry_ts_hist = Counter()
    checked = set()

    for title, data in titles.items():
        for e in data:
            sec = parse_ts(e.get('timestamp'))
            if sec is None:
                continue
            if sec < 240:
                op_entries += 1
            if sec >= TAIL_START:
                tail_entries += 1
            entry_ts_hist[sec // 60] += 1
            f = MAP.get(f'{title}|{e["timestamp"]}')
            if not f or f in checked:
                continue
            checked.add(f)
            p = os.path.join(FR, f)
            img = cv2.imread(p)
            if img is None:
                continue
            n_frame += 1
            segs = split_lines(img, SCAN_TOP, SCAN_BOT)
            if not segs:
                continue
            # 白像素最密的一段视为主文字行
            main = max(segs, key=lambda s: s[2])
            top_hist[main[0] // 20 * 20] += 1
            bottom_hist[main[1] // 20 * 20] += 1
            if len(segs) == 1:
                n_line1 += 1
            else:
                n_line2 += 1
                multi.append({'f': f, 'segs': segs})
            if main[1] > BAND[1] + 4:
                cut_by_band += 1
            if main[0] > BAND[1]:
                below_only += 1

    lines = [
        f'抽查帧 {n_frame}(去重后) —— 单文字行 {n_line1} / 多文字行 {n_line2}',
        f'主文字行下缘 > 985 的帧: {cut_by_band} ({cut_by_band * 100.0 / max(1, n_frame):.1f}%)',
        f'主文字行完全在 985 以下的帧: {below_only}',
        f'主文字行上缘分布(按20px桶): {sorted(top_hist.items())}',
        f'主文字行下缘分布(按20px桶): {sorted(bottom_hist.items())}',
        f'条目时间分布(分钟桶): {sorted(entry_ts_hist.items())}',
        f'OP 段(0~4m)条目 {op_entries} / 片尾段(>={TAIL_START // 60}m{TAIL_START % 60}s)条目 {tail_entries}'
        f' / 合计 {sum(len(v) for v in titles.values())}',
    ]
    out = '\n'.join(lines)
    open(os.path.join(B, 'review', 'q_geom.txt'), 'w', encoding='utf-8').write(out)
    json.dump({'multi': multi[:2000], 'n_frame': n_frame, 'multi_n': len(multi)},
              open(os.path.join(B, 'review', 'q_geom.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(out)


if __name__ == '__main__':
    main()
