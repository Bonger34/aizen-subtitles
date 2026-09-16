# -*- coding: utf-8 -*-
"""
make_contact_sheet.py — 把 cont_cands.json 的候选帧拼成拼图(每图 2 行三列多块), 供人工快速验证
输出: review/cont_sheets/[ep]_sNN.jpg
用法: python make_contact_sheet.py [Pxx ...]  (缺省全部有候选的集)
"""
import glob
import json
import os
import sys

import cv2
import numpy as np

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
OUT = os.path.join(BASE, 'review', 'cont_sheets')
PER = 12   # 每张拼图 12 帧


def main():
    os.makedirs(OUT, exist_ok=True)
    cands = json.load(open(os.path.join(BASE, 'review', 'cont_cands.json'), encoding='utf-8'))
    eps = sys.argv[1:] or list(cands.keys())
    for ep in eps:
        rows = cands.get(ep, [])
        if not rows:
            continue
        # 帧图: 高 90 宽 1720 → 缩放为 高 108 宽 2064(放大到原字幕带的 60%? 太小)
        # 缩放到宽 980(配合 3 列 ~ 2940 宽); 高 = 980*90/1720 ≈ 51px 太扁, 放大 2 倍: 宽1960 高102
        frames = []
        for c in rows:
            fp = c.get('frame')
            if fp and os.path.exists(fp):
                frames.append(fp)
        if not frames:
            continue
        print(f'{ep}: {len(frames)} 帧', flush=True)
        for si in range(0, len(frames), PER):
            chunk = frames[si:si + PER]
            imgs = []
            for fp in chunk:
                img = cv2.imread(fp)
                if img is None:
                    continue
                img = cv2.resize(img, (1960, 102), interpolation=cv2.INTER_AREA)
                # 顶部加序号条
                bar = np.full((26, 1960, 3), 40, dtype=np.uint8)
                idx = len(imgs)
                cv2.putText(bar, f'{si + idx}: {os.path.basename(fp)[:16]}', (10, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                imgs.append(np.vstack([bar, img]))
            if not imgs:
                continue
            # 3 列网格, 每格间 4px 白边
            pad = 4
            cols = 3
            h = imgs[0].shape[0] + pad
            w = imgs[0].shape[1] + pad
            cell = np.full((h, w, 3), 255, dtype=np.uint8)
            cell[0:imgs[0].shape[0], 0:imgs[0].shape[1]] = imgs[0]
            nrows = (len(imgs) + cols - 1) // cols
            rows_imgs = []
            for r in range(nrows):
                row_cells = []
                for c in range(cols):
                    i = r * cols + c
                    cc = cell.copy()
                    if i < len(imgs):
                        cc[0:imgs[i].shape[0], 0:imgs[i].shape[1]] = imgs[i]
                    row_cells.append(cc)
                rows_imgs.append(np.hstack(row_cells))
            sheet = np.vstack(rows_imgs)
            out = os.path.join(OUT, f'{ep}_s{si // PER + 1:02d}.jpg')
            cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
            print(f'   -> {out}', flush=True)


if __name__ == '__main__':
    main()
