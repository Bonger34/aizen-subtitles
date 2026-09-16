# -*- coding: utf-8 -*-
"""
scan_cont_state.py — 状态驱动采样版(验证短句覆盖)
与 scan_cont.py 的区别: 采样点不再按固定 0.7s 打点, 而是
  1. 区间首帧 / 末帧 / 白像素峰值帧
  2. 白像素占比相对上一采样点变化 > CHANGE_TH 的帧(字幕切换)
  3. 兜底: 距上一采样点 >= FALLBACK_S 秒
这样每次字幕切换必打点, 短句(显示 <0.7s)也能覆盖。

用法: SCAN_TAG=state_ python scan_cont_state.py P01 P13
"""
import json
import os
import re
import sys

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
_ORT124 = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124'
if os.path.isdir(_NV_DLL):
    try:
        os.add_dll_directory(_NV_DLL)
        os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
    except Exception as e:
        print(f'DLL 目录注册失败: {e}', flush=True)
if os.path.isdir(_ORT124):
    sys.path.insert(0, _ORT124)

import cv2
import numpy as np
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO_DIR = os.path.join(BASE, 'Videos')
CLEAN = os.path.join(BASE, 'subtitle_clean')
OUT_DIR = os.path.join(BASE, 'review', 'cont_frames')
AREA = (100, 895, 1820, 985)
ON_TH = float(os.environ.get('SCAN_ON_TH', '0.02'))
OFF_TH = float(os.environ.get('SCAN_OFF_TH', '0.01'))
CHANGE_TH = float(os.environ.get('SCAN_CHANGE_TH', '0.05'))   # 白像素相对变化阈值
FALLBACK_S = float(os.environ.get('SCAN_FALLBACK_S', '1.2'))  # 兜底采样间隔(秒)
MIN_GAP = int(os.environ.get('SCAN_MIN_GAP', '2'))            # 采样点最小间隔(帧)
TAG = os.environ.get('SCAN_TAG', 'state_')
LIB_WIN = 5
BEF_TAU = 0.6


def norm(s):
    return re.sub(r'[，。！？、；：“”‘’\s]', '', s)


def binarize(crop):
    arr = crop.copy()
    mask = np.all(arr > 245, axis=2)
    arr[mask] = [255, 255, 255]
    arr[~mask] = [0, 0, 0]
    return arr


def load_lib(ep):
    for f in os.listdir(CLEAN):
        if f.startswith(f'[{ep}]') and f.endswith('.json'):
            arr = json.load(open(os.path.join(CLEAN, f), encoding='utf-8'))
            break
    else:
        return []
    lib = []
    for e in arr:
        ts = e.get('timestamp') or ''
        m = re.match(r'(\d+)m(\d+)s', ts)
        t = norm(e.get('text') or '')
        if m and t:
            lib.append((int(m.group(1)) * 60 + int(m.group(2)), t))
    return lib


def find_video(ep):
    for v in os.listdir(VIDEO_DIR):
        if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4'):
            return os.path.join(VIDEO_DIR, v)
    return None


def scan_episode(ep, ocr):
    video = find_video(ep)
    if not video:
        return
    lib = load_lib(ep)
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f'== {ep} {total}帧 fps={fps:.2f} 库{len(lib)}条 ==', flush=True)

    # 第 1 遍: 记录白像素序列 + 区间
    wseries = []
    intervals = []
    state = 'off'
    cur_start = None
    fidx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        crop = frame[AREA[1]:AREA[3], AREA[0]:AREA[2]]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        wr = float((gray > 245).mean())
        wseries.append(wr)
        if state == 'off':
            if wr > ON_TH:
                state = 'on'
                cur_start = fidx
        else:
            if wr < OFF_TH:
                intervals.append((cur_start, fidx - 1))
                state = 'off'
                cur_start = None
        fidx += 1
    if state == 'on':
        intervals.append((cur_start, fidx - 1))
    cap.release()
    print(f'  字幕区间: {len(intervals)}', flush=True)

    # 采样点选择
    fallback_frames = max(1, int(FALLBACK_S * fps))
    pts = set()
    for s, e in intervals:
        seg = wseries[s:e + 1]
        if not seg:
            continue
        pts.add(s)
        pts.add(e)
        pts.add(s + int(np.argmax(seg)))
        last = s
        for i in range(s + 1, e + 1):
            base = max(wseries[last], 0.001)
            if abs(wseries[i] - wseries[last]) / base > CHANGE_TH:
                if i - last >= MIN_GAP:
                    pts.add(i)
                    last = i
            elif i - last >= fallback_frames:
                pts.add(i)
                last = i
    samples = sorted(pts)
    print(f'  采样点: {len(samples)}', flush=True)

    ep_out = os.path.join(OUT_DIR, ep)
    os.makedirs(ep_out, exist_ok=True)

    # 第 2 遍: 顺序读, 提取采样帧
    cap = cv2.VideoCapture(video)
    saved = {}
    want = set(samples)
    fidx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if fidx in want:
            crop = frame[AREA[1]:AREA[3], AREA[0]:AREA[2]]
            fname = f'{ep}_{fidx:06d}_s.jpg'
            fpath = os.path.join(ep_out, fname)
            cv2.imwrite(fpath, crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
            saved[fidx] = fpath
        fidx += 1
        if fidx > total:
            break
    cap.release()

    # OCR
    ocr_results = {}
    for i, t in enumerate(samples):
        if i % 200 == 0:
            print(f'  ... OCR {i+1}/{len(samples)}', flush=True)
        fpath = saved.get(t)
        if not fpath:
            continue
        img = cv2.imread(fpath)
        if img is None:
            continue
        try:
            res = ocr(binarize(img))
        except Exception:
            continue
        txt = ''.join(res.txts) if res.txts else ''
        tn = ''.join(re.findall(r'[\u4e00-\u9fff]', txt))
        ocr_results[t] = (tn, txt)

    # 聚合 → 序列
    seqs = []
    for t in samples:
        if t not in ocr_results:
            continue
        tn, raw = ocr_results[t]
        if len(tn) < 2:
            continue
        seqs.append({'t': f'{round(t / fps) // 60}m{round(t / fps) % 60:02d}s',
                     'text': tn, 'raw': raw, 'fidx': t})

    # 库匹配
    cands = []
    for s in seqs:
        sec = round(s['fidx'] / fps)
        win = [lt for ts, lt in lib if abs(ts - sec) <= LIB_WIN]
        if win:
            bef = max(sum(1 for c in s['text'] if c in w) / len(s['text']) for w in win)
            if bef >= BEF_TAU:
                continue
        cands.append(s)
    out = os.path.join(BASE, 'review', f'{TAG}cont_{ep}.json')
    json.dump({'ep': ep, 'fps': fps, 'total': total, 'intervals': len(intervals),
               'samples': len(samples), 'seqs': seqs, 'cands': cands, 'lib': len(lib)},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'  采样 {len(samples)} 帧, 序列 {len(seqs)}, 候选 {len(cands)} -> {out}', flush=True)


def main():
    eps = sys.argv[1:] or ['P01']
    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH,
        'Rec.rec_img_shape': [3, 48, 1536],
        'Rec.rec_batch_num': 1,
    })
    print('OCR 就绪', flush=True)
    for ep in eps:
        scan_episode(ep, ocr)


if __name__ == '__main__':
    main()
