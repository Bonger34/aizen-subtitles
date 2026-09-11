# -*- coding: utf-8 -*-
"""找出"主文字行带伸出字幕带下缘"的已存帧 —— 这些帧的库文本很可能是被裁切后的碎片。

判据: 近白像素行分布中, 落在 y∈[850,1062] 的主文字行带, 其下边界 > 991(带下缘 985 + 6px 容差)。
输出 review/low_text_frames.json
"""
import json
import os

import cv2
import numpy as np

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'Web', 'frames')
BAND_BOT = 985
LIMIT = 1062

hits = []
files = sorted(os.listdir(FR))
for i, f in enumerate(files):
    if i % 1000 == 0:
        print(f'  {i}/{len(files)}', flush=True)
    img = cv2.imread(os.path.join(FR, f))
    if img is None:
        continue
    h, w = img.shape[:2]
    sy = 1080.0 / h
    b, g, r = img[:, :, 0].astype(np.int16), img[:, :, 1].astype(np.int16), img[:, :, 2].astype(np.int16)
    mask = np.minimum(np.minimum(b, g), r) > 225
    prof = mask.sum(axis=1)
    if prof.max() < 5:
        continue
    thr = max(3, int(prof.max() * 0.4))
    # 把满足阈值的行切成连续段(间隔 >6px 视为不同文字行)
    ys = [y for y in range(h) if prof[y] >= thr]
    runs = []
    for y in ys:
        if runs and y - runs[-1][1] <= 6:
            runs[-1][1] = y
        else:
            runs.append([y, y])
    # 取与标准字幕带 [895,985] 重叠最多的那一段, 作为"字幕行"
    def ov(r):
        return max(0, min(r[1] * sy, BAND_BOT) - max(r[0] * sy, 850))
    if not runs:
        continue
    sub = max(runs, key=ov)
    y0, y1 = sub[0] * sy, sub[1] * sy
    if ov(sub) <= 0:
        continue
    if y1 > BAND_BOT + 6:
        hits.append({'f': f, 'y0': round(y0), 'y1': round(y1),
                     'below': round(y1 - BAND_BOT)})

hits.sort(key=lambda x: -x['below'])
json.dump(hits, open(os.path.join(B, 'review', 'low_text_frames.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'扫描 {len(files)} 帧, 主文字行带伸出字幕带下缘的 {len(hits)} 帧')
for x in hits[:15]:
    print(f"   {x['f']:18s} y={x['y0']}-{x['y1']} 超出 {x['below']}px")
