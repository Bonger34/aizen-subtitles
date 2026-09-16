# -*- coding: utf-8 -*-
"""统计已存帧中"字幕文字行"的纵向位置, 量化当前字幕带 (895~985) 的裁切情况。

对每张帧取近白像素的行分布, 找出主文字行带(最大行带), 记录其 y 区间(1080p 坐标),
统计: 上边界 < 895 / 下边界 > 985 的比例。
"""
import os
import random

import cv2
import numpy as np

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'docs', 'frames')
N = 1500
TOPB, BOTB = 895, 985

files = sorted(os.listdir(FR))
sample = random.Random(3).sample(files, min(N, len(files)))
above = below = both_ok = nodata = 0
ex_above, ex_below = [], []
for f in sample:
    img = cv2.imread(os.path.join(FR, f))
    if img is None:
        continue
    h, w = img.shape[:2]
    sy = 1080.0 / h
    b, g, r = img[:, :, 0].astype(np.int16), img[:, :, 1].astype(np.int16), img[:, :, 2].astype(np.int16)
    mask = np.minimum(np.minimum(b, g), r) > 225
    prof = mask.sum(axis=1)
    if prof.max() < 5:
        nodata += 1
        continue
    thr = max(3, int(prof.max() * 0.5))
    ys = np.where(prof >= thr)[0]
    # 取字幕带内的主行带; 若无则取全图最大行带
    inb = ys[(ys * sy >= TOPB - 40) & (ys * sy <= BOTB + 60)]
    sel = inb if len(inb) else ys
    y0, y1 = sel.min() * sy, sel.max() * sy
    if y0 < TOPB - 6:
        above += 1
        if len(ex_above) < 5:
            ex_above.append((f, round(y0), round(y1)))
    elif y1 > BOTB + 6:
        below += 1
        if len(ex_below) < 8:
            ex_below.append((f, round(y0), round(y1)))
    else:
        both_ok += 1

tot = above + below + both_ok
lines = [f'抽样 {len(sample)} 张已存帧(近白文字行分析), 有效 {tot}, 无文字 {nodata}',
         f'  文字行带上边界高于 {TOPB}: {above} ({above / max(1, tot) * 100:.1f}%)',
         f'  文字行带下边界低于 {BOTB}: {below} ({below / max(1, tot) * 100:.1f}%)',
         f'  完全落在字幕带内: {both_ok} ({both_ok / max(1, tot) * 100:.1f}%)',
         '', f'  上溢样例(帧名, y0, y1): {ex_above}', f'  下溢样例(帧名, y0, y1): {ex_below}']
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'band_clip.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
