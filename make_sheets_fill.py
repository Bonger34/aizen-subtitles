# -*- coding: utf-8 -*-
"""make_sheets_fill.py — 把 cont_fill_{ep}.json 的新帧图拼成联系表(3列x4行), 供人工抽查
用法: python make_sheets_fill.py P01
"""
import json
import os
import sys

import cv2
import numpy as np

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FRAMES = os.path.join(BASE, 'docs', 'frames')
OUTD = os.path.join(BASE, 'review', 'cont_sheets')


def main():
    ep = sys.argv[1]
    os.makedirs(OUTD, exist_ok=True)
    got = json.load(open(os.path.join(BASE, 'review', f'cont_fill_{ep}.json'), encoding='utf-8'))
    secs = sorted(int(k) for k in got.keys())
    rows = 4
    cols = 3
    cell_w, cell_h = 320, 180
    pad = 6
    per_sheet = rows * cols
    for si, s0 in enumerate(range(0, len(secs), per_sheet)):
        chunk = secs[s0:s0 + per_sheet]
        cells = []
        for k in chunk:
            info = got[str(k)]
            fp = os.path.join(FRAMES, info['frame'])
            img = cv2.imread(fp)
            if img is None:
                img = np.zeros((cell_h, cell_w, 3), dtype=np.uint8)
            else:
                img = cv2.resize(img, (cell_w, cell_h), interpolation=cv2.INTER_AREA)
            # 底部文本条: 秒 + 文本
            bar = np.full((22, cell_w, 3), 30, dtype=np.uint8)
            cv2.putText(bar, f'{info["ts"]} {info["text"]}', (4, 17),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
            cells.append(np.vstack([img, bar]))
        # 网格
        grid = []
        for r in range(rows):
            line = []
            for c in range(cols):
                i = r * cols + c
                cell = cells[i] if i < len(cells) else np.zeros((cell_h + 22, cell_w, 3), dtype=np.uint8)
                padarr = np.full((cell.shape[0] + pad, cell.shape[1] + pad, 3), 255, dtype=np.uint8)
                padarr[pad // 2:pad // 2 + cell.shape[0], pad // 2:pad // 2 + cell.shape[1]] = cell
                line.append(padarr)
            grid.append(np.hstack(line))
        sheet = np.vstack(grid)
        out = os.path.join(OUTD, f'{ep}_fill_s{si + 1:02d}.jpg')
        cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(out, flush=True)


if __name__ == '__main__':
    main()
