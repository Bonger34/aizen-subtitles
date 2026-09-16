# -*- coding: utf-8 -*-
"""最后 2 条的扩窗扫描(定稿): ±120s 内逐帧detect字幕区间 -> 每区间只 OCR 峰值帧。

判定:
  * 区间 OCR 文本能对上库中附近条目 -> 该字幕已被收录
  * 对不上且长度>=2 -> 库中缺失的字幕(列出)
  * 区间 OCR 命中目标文本(口 / 敬告) -> 该条目真身在此
成本约为"每 0.25s 全采样"的 1/20。
"""
import json
import os
import re

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
_ORT124 = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124'
import sys
if os.path.isdir(_NV_DLL):
    os.add_dll_directory(_NV_DLL)
    os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
if os.path.isdir(_ORT124):
    sys.path.insert(0, _ORT124)

import cv2
import numpy as np
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle_clean')
OUT = os.path.join(B, 'review', 'residue_window2.txt')
TARGETS = [('P22', '17m53s', '口'), ('P24', '18m11s', '敬告')]
WIN = 120
BAND = (100, 895, 1820, 985)
CROP = (100, 880, 1820, 1050)
ON_TH, OFF_TH = 0.02, 0.01


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def bef(want, got):
    return sum(1 for ch in want if ch in got) / len(want) if want and got else 0.0


ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
lines = [f'最后 2 条: ±{WIN}s 窗口内字幕区间检测 + 每区间峰值帧 OCR', '']
for ep, ts, want_raw in TARGETS:
    base = sec_of(ts)
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    lib = [(sec_of(e['timestamp']), norm(e.get('text'))) for e in
           json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))]
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    lo, hi = max(0, base - WIN), base + WIN
    sf, ef = int(lo * fps), min(total - 1, int(hi * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, sf)
    ivs, state, s0, peak, pr, n = [], 'off', None, None, 0.0, sf
    while n <= ef:
        ok, fr = cap.read()
        if not ok:
            break
        n += 1
        g = cv2.cvtColor(fr[BAND[1]:BAND[3], BAND[0]:BAND[2]], cv2.COLOR_BGR2GRAY)
        wr = float((g > 245).mean())
        if state == 'off':
            if wr > ON_TH:
                state, s0, peak, pr = 'on', n, n, wr
        else:
            if wr > pr:
                pr, peak = wr, n
            if wr < OFF_TH:
                ivs.append((s0, n - 1, peak))
                state = 'off'
    if state == 'on':
        ivs.append((s0, n - 1, peak))
    cap.release()
    print(f'{ep} {ts}: 窗口 {lo // 60}m{lo % 60:02d}s~{hi // 60}m{hi % 60:02d}s, 区间 {len(ivs)}', flush=True)

    lines.append(f'=== {ep} {ts}  目标=[{want_raw}]  区间 {len(ivs)} 段')
    miss, hit = [], []
    cap = cv2.VideoCapture(find_video(ep))
    for a, b, pk in ivs:
        s = pk / fps
        cap.set(cv2.CAP_PROP_POS_FRAMES, pk)
        ok, fr = cap.read()
        if not ok:
            continue
        h, w = fr.shape[:2]
        sy = h / 1080.0
        cr = fr[int(CROP[1] * sy):int(CROP[3] * sy), int(CROP[0] * (w / 1920.0)):int(CROP[2] * (w / 1920.0))]
        cr = cv2.resize(cr, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
        best = ''
        for th in (245, 235):
            arr = cr.copy()
            mk = np.all(arr > th, axis=2)
            arr[mk] = [255, 255, 255]
            arr[~mk] = [0, 0, 0]
            try:
                rr = ocr(arr)
                t = norm(''.join(rr.txts) if rr.txts else '')
            except Exception:
                t = ''
            if len(t) > len(best):
                best = t
        if len(best) < 2:
            continue                      # 无文字 -> 画面白闪/误检
        near = [(lt, lx) for lt, lx in lib if abs(lt - s) <= 3]
        ok_cov = any(bef(best, lx) >= 0.6 or bef(lx, best) >= 0.6 for _, lx in near)
        tag = '已收录' if ok_cov else '★库中缺失★'
        if not ok_cov:
            miss.append((s, best))
        if norm(want_raw) in best:
            hit.append((s, best))
        lines.append(f'   [{int(s) // 60:02d}m{s % 60:05.2f}s 峰{a}-{b}] {tag} ocr=[{best}] 近邻={[x for _, x in near][:2]}')
    cap.release()
    lines.append(f'  --> 目标文本命中: {len(hit)} {hit}')
    lines.append(f'  --> 库中缺失的字幕 {len(miss)} 条: {miss[:10]}')
    lines.append('')
txt = '\n'.join(lines)
open(OUT, 'w', encoding='utf-8').write(txt)
print(txt)
