# -*- coding: utf-8 -*-
"""对"孤儿帧 vs 库条目配图"做像素比对, 判定是否为同一张图(即命名偏移造成的重复)。"""
import json
import os

import cv2
import numpy as np

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'Web', 'frames')
fm = open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read()
m = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])

# 孤儿帧 -> 库中同文本条目的 key(格式 [Pxx]名|秒)
PAIRS = [
    ('P20_24m30s.jpg', '[P20]20 我们互相仇视对方|24m16s'),
    ('P25_23m18s.jpg', None),
    ('P25_22m26s.jpg', None),
    ('P25_23m10s.jpg', None),
]


def find_key(ep, sec_text):
    for k, v in m.items():
        if k.startswith(f'[{ep}]') and k.endswith('|' + sec_text):
            return k, v
    return None, None


def gray(p):
    img = cv2.imread(p)
    if img is None:
        return None
    return cv2.cvtColor(cv2.resize(img, (240, 135)), cv2.COLOR_BGR2GRAY).astype(np.int16)


lines = []
for orphan, key in PAIRS:
    ep = orphan[:3]
    if key is None:
        # 按文本反查: 用 OCR 结果定位库条目
        continue
    if key not in m:
        lines.append(f'{orphan}: 找不到库条目 {key}')
        continue
    k, mapped = find_key(ep, key.split('|')[1])
    a, b = gray(os.path.join(FR, orphan)), gray(os.path.join(FR, mapped))
    if a is None or b is None:
        lines.append(f'{orphan} vs {mapped}: 读图失败 (orphan={a is not None}, mapped={b is not None})')
        continue
    mad = float(np.abs(a - b).mean())
    same = np.array_equal(a, b)
    lines.append(f'{orphan}  vs  {mapped}   平均差={mad:.2f} 完全相同={same}')

txt = '\n'.join(lines)
print(txt)
open(os.path.join(B, 'review', 'orphan_vs_map_pix.txt'), 'w', encoding='utf-8').write(txt)
