# -*- coding: utf-8 -*-
"""最后 2 条的扩窗密扫(省算力版): 先在 ±120s 窗口内逐帧检测字幕区间, 再只对区间内密采 OCR。

1) 顺序读窗口内每一帧, 用字幕带白像素占比(>245, ON=0.02/OFF=0.01)切出区间 —— 无遗漏;
2) 每个区间内每 0.25s 取帧, 用 3 种裁剪 × 2 阈值 OCR;
3) 报告: 是否出现目标文本; 以及该窗口内所有区间读到的文本(便于人工判断该条是否本就无字幕)。
"""
import json
import os
import re
import sys

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
_ORT124 = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124'
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
OUT = os.path.join(B, 'review', 'residue_window.txt')
TARGETS = [('P22', '17m53s', '口'), ('P24', '18m11s', '敬告')]
WIN = 120
BAND = (100, 895, 1820, 985)
CROPS = {'band': (100, 880, 1820, 1050), 'low': (100, 700, 1820, 1078),
         'top': (100, 40, 1820, 300)}
ON_TH, OFF_TH = 0.02, 0.01
STEP = 0.25


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def load_lib(ep):
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    return [(sec_of(e['timestamp']), e.get('text') or '')
            for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))]


def crop_for(frame, box):
    h, w = frame.shape[:2]
    sy = h / 1080.0
    c = frame[int(box[1] * sy):int(box[3] * sy), int(box[0] * (w / 1920.0)):int(box[2] * (w / 1920.0))]
    return cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)


ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})

lines = [f'最后 2 条: ±{WIN}s 窗口内的字幕区间检测 + 区间内密采 OCR', '']
for ep, ts, want_raw in TARGETS:
    base = sec_of(ts)
    lo, hi = max(0, base - WIN), base + WIN
    lib = load_lib(ep)
    cap = cv2.VideoCapture(find_video(ep))
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    start_f, end_f = int(lo * fps), min(total - 1, int(hi * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)

    # ---- 逐帧检测字幕带区间 ----
    ivs, state, s0 = [], 'off', None
    n = start_f
    while n <= end_f:
        ok, fr = cap.read()
        if not ok:
            break
        n += 1
        g = cv2.cvtColor(fr[BAND[1]:BAND[3], BAND[0]:BAND[2]], cv2.COLOR_BGR2GRAY)
        wr = float((g > 245).mean())
        sec = n / fps
        if state == 'off':
            if wr > ON_TH:
                state, s0 = 'on', sec
        elif wr < OFF_TH:
            ivs.append((round(s0, 2), round(sec, 2)))
            state = 'off'
    if state == 'on':
        ivs.append((round(s0, 2), round(n / fps, 2)))
    cap.release()
    lines.append(f'=== {ep} {ts}  目标=[{want_raw}]  窗口 {lo // 60}m{lo % 60:02d}s~{hi // 60}m{hi % 60:02d}s'
                 f'  检出字幕区间 {len(ivs)} 段')

    # ---- 区间内密采 OCR ----
    cap = cv2.VideoCapture(find_video(ep))
    hits = []
    covered = 0
    for a, b in ivs:
        txts = {}
        d = 0.0
        while a + d <= b:
            s = a + d
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(s * fps)))
            ok, fr = cap.read()
            if ok:
                for cname, box in CROPS.items():
                    cr = crop_for(fr, box)
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
                        if len(t) >= 2:
                            txts[t] = txts.get(t, 0) + 1
            d += STEP
        best = sorted(txts.items(), key=lambda x: (-x[1], -len(x[0])))[:3]
        ins = [t for t in txts if norm(want_raw) in t]
        near = [lt for lt, _ in lib if abs(lt - (a + b) / 2) <= 3]
        if near:
            covered += 1
        lines.append(f"   [{a // 60}m{a % 60:05.2f}s-{b // 60}m{b % 60:05.2f}s] "
                     f"库内已有={near[:2]} 读出={[t for t, _ in best]}")
        if ins:
            hits.append((a, b, ins))
    cap.release()
    lines.append(f'  --> 目标文本出现次数: {len(hits)}; 该窗口内被库条目覆盖的区间 {covered}/{len(ivs)}')
    for a, b, ins in hits:
        lines.append(f'      命中区间 [{a}-{b}] {ins}')
    lines.append('')
txt = '\n'.join(lines)
open(OUT, 'w', encoding='utf-8').write(txt)
print(txt)
