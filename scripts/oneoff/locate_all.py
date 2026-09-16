# -*- coding: utf-8 -*-
"""单次顺序读全片, 批量定位参考图的真实时间, 结果写 JSON。

用法: python locate_all.py P25 reflist.json out.json
"""
import json
import os
import sys

import cv2
import numpy as np

V = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\Videos'
F = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\docs\frames'


def small(img):
    return cv2.cvtColor(cv2.resize(img, (240, 135)), cv2.COLOR_BGR2GRAY).astype(np.int16)


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def main():
    ep, listfile, outfile = sys.argv[1], sys.argv[2], sys.argv[3]
    refs = json.load(open(listfile, encoding='utf-8'))
    mats = []
    for r in refs:
        p = os.path.join(F, r)
        img = cv2.imread(p)
        if img is not None:
            mats.append((r, small(img)))
    print(f'参考图 {len(mats)} 张, 开始逐帧定位', flush=True)
    best = {r: [] for r, _ in mats}
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        n += 1
        if n % 2:
            continue
        sm = small(fr)
        sec = int(round(n / fps))
        for r, m in mats:
            best[r].append((float(np.abs(sm - m).mean()), sec))
    cap.release()
    res = {}
    for r, _ in mats:
        best[r].sort()
        seen, top = set(), []
        for mad, sec in best[r]:
            if sec in seen:
                continue
            seen.add(sec)
            top.append([sec, round(mad, 2)])
            if len(top) >= 3:
                break
        res[r] = top
    json.dump({'fps': fps, 'frames': n, 'result': res},
              open(outfile, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'写出 {outfile}', flush=True)
    for r in refs:
        if r in res:
            t = res[r][0]
            print(f"  {r:18s} -> {t[0] // 60}m{t[0] % 60:02d}s (MAD={t[1]})  次选 "
                  f"{res[r][1][0] // 60}m{res[r][1][0] % 60:02d}s(MAD={res[r][1][1]})", flush=True)


if __name__ == '__main__':
    main()
