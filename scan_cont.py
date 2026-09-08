# -*- coding: utf-8 -*-
"""
scan_cont.py — C方案重做(连续读帧版)
全程顺序 cap.read(),绝不 cap.set(POS_MSEC) 重定位 —— 消除帧错位。

流程(每集):
  1. 顺序读全部帧, 统计字幕带(SUBTITLE_AREA)白像素占比 white_ratio
  2. 状态机 ON/OFF(ON>0.02, OFF<0.01)切出字幕区间 (start..end)
  3. 区间内按 ~0.7s 采样多帧 crop(含峰值帧), 落盘 jpg(OCR/人工验证同一帧)
  4. 二值化后 RapidOCR(GPU), 提文本
  5. 与库 ±5s 匹配, bef<0.6 → 漏句候选
用法: python scan_cont.py [Pxx ...]   不带参数 = 全部 25 集
"""
import json
import os
import re
import sys

# CUDA/cuDNN DLL 位于 workspace(_nv_dlls), 必须在导入 onnxruntime 前注册搜索目录
# ORT 1.24.4(CUDA12 链) 从 workspace(_ort124) 前置, 替代 site-packages 的 1.29(CUDA13, 与驱动不兼容)
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
AREA = (100, 895, 1820, 985)          # x0,y0,x1,y1 (1920x1080 字幕带)
ON_TH = 0.02          # 白像素占比达到视为字幕出现
OFF_TH = 0.01         # 回落到视为字幕消失(滞后防抖)
SAMPLE_STEP = 0.7     # 区间内采样间隔(秒)
LIB_WIN = 5           # 库匹配窗口 ±5s
BEF_TAU = 0.6         # 字符重合度低于此视为漏句


def norm(s):
    return re.sub(r'[，。！？、；：“”‘’\s]', '', s)


def binarize(crop):
    """与 CutSubtitle_rapidocr.py 一致: RGB>245 保留, 其余置黑"""
    arr = crop.copy()
    mask = np.all(arr > 245, axis=2)
    arr[mask] = [255, 255, 255]
    arr[~mask] = [0, 0, 0]
    return arr


def load_lib(ep):
    """返回 [(秒, 规范化文本)]"""
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
    """单集扫描, 返回 (候选列表, 统计)"""
    video = find_video(ep)
    if not video:
        return [], {'error': 'no video'}
    lib = load_lib(ep)

    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f'== {ep} {total}帧 fps={fps:.2f} 库{len(lib)}条 ==', flush=True)

    # ---- 第 1 遍: 连续顺序读, 白像素状态机切区间 ----
    intervals = []            # (start_fidx, end_fidx, peak_fidx)
    state = 'off'
    cur_start = cur_peak = cur_peak_ratio = None
    fidx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        crop = frame[AREA[1]:AREA[3], AREA[0]:AREA[2]]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        wr = float((gray > 245).mean())
        if state == 'off':
            if wr > ON_TH:
                state = 'on'
                cur_start = cur_peak = fidx
                cur_peak_ratio = wr
        else:
            if wr > cur_peak_ratio:
                cur_peak_ratio = wr
                cur_peak = fidx
            if wr < OFF_TH:
                intervals.append((cur_start, fidx - 1, cur_peak))
                state = 'off'
                cur_start = cur_peak = cur_peak_ratio = None
        fidx += 1
    if state == 'on':
        intervals.append((cur_start, fidx - 1, cur_peak))
    cap.release()
    print(f'  字幕区间: {len(intervals)}', flush=True)

    # ---- 区间内采样帧: 每 ~0.7s 一帧(含首帧/峰值帧), 连续重读取帧 ----
    samples = []              # (fidx, 区间序号)
    for i, (s, e, p) in enumerate(intervals):
        # 采样位置: 首帧, 然后每 SAMPLE_STEP 秒, 最后峰值帧 (去重/排序)
        times = [s]
        k = 1
        while s + k * SAMPLE_STEP * fps < e:
            times.append(s + int(k * SAMPLE_STEP * fps))
            k += 1
        times.append(p)
        times.sort()
        seen = set()
        for t in times:
            if t not in seen:
                seen.add(t)
                samples.append((t, i))

    ep_out = os.path.join(OUT_DIR, ep)
    os.makedirs(ep_out, exist_ok=True)

    # ---- 第 2 遍: 连续顺序读(重新 open, 仍不 seek), 到采样帧取 crop 落盘 ----
    cap = cv2.VideoCapture(video)
    texts = {}                # (区间号, 采样文本norm) -> 记录
    saved = {}                # fidx -> 文件路径
    want = {t: i for t, i in samples}
    fidx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if fidx in want:
            crop = frame[AREA[1]:AREA[3], AREA[0]:AREA[2]]
            i = want[fidx]
            fname = f'{ep}_{fidx:06d}_{i}.jpg'
            fpath = os.path.join(ep_out, fname)
            cv2.imwrite(fpath, crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
            saved[fidx] = fpath
        fidx += 1
        if fidx > total:
            break
    cap.release()

    # ---- OCR 采样帧 → 文本 → 库匹配 ----
    ocr_results = {}          # fidx -> [(text_norm, raw)]
    for fidx_i, (t, i) in enumerate(samples):
        if fidx_i % 100 == 0:
            print(f'  ... OCR {fidx_i+1}/{len(samples)}', flush=True)
        fpath = saved.get(t)
        if not fpath:
            continue
        img = cv2.imread(fpath)
        if img is None:
            continue
        try:
            res = ocr(binarize(img))
        except Exception as ex:
            print(f'  OCR err fidx={t}: {ex}', flush=True)
            continue
        txt = ''.join(res.txts) if res.txts else ''
        txt_n = ''.join(re.findall(r'[\u4e00-\u9fff]', txt))
        ocr_results[t] = (txt_n, txt)

    # 按区间聚合: 区间内文本去重(相邻重复算一个), 逐文本查库
    by_int = {}
    for (t, i) in samples:
        if t in ocr_results:
            by_int.setdefault(i, []).append((t, ocr_results[t][0], ocr_results[t][1]))

    cands = []
    for i, rows in sorted(by_int.items()):
        s, e, p = intervals[i]
        # 去重: 相邻采样文本相同(或互为子串)时保留首次
        uniq = []
        for t, tn, raw in rows:
            if uniq and (tn == uniq[-1][1] or (len(tn) >= 2 and tn in uniq[-1][1])):
                continue
            uniq.append((t, tn, raw))
        for t, tn, raw in uniq:
            if len(tn) < 2:
                continue
            sec = round(t / fps)
            win = [lt for ts, lt in lib if abs(ts - sec) <= LIB_WIN]
            hit = False
            if win:
                bef = max(sum(1 for c in tn if c in w) / len(tn) for w in win) if tn else 0
                hit = bef >= BEF_TAU
            if not hit:
                cands.append({
                    't': f'{sec // 60}m{sec % 60:02d}s',
                    'text': tn,
                    'raw': raw,
                    'fidx': t,
                    'frame': saved[t],
                    'int': i,
                })

    # 输出
    seqs = []
    for i, rows in sorted(by_int.items()):
        # 去重: 相邻采样文本相同(或互为子串)时保留首次
        uniq = []
        for t, tn, raw in rows:
            if uniq and (tn == uniq[-1][1] or (len(tn) >= 2 and tn in uniq[-1][1])):
                continue
            uniq.append((t, tn, raw))
        for t, tn, raw in uniq:
            seqs.append({'t': f'{round(t / fps) // 60}m{round(t / fps) % 60:02d}s',
                         'text': tn, 'raw': raw, 'fidx': t})
    out = os.path.join(BASE, 'review', f'cont_{ep}.json')
    json.dump({'ep': ep, 'fps': fps, 'total': total,
               'intervals': len(intervals), 'samples': len(samples),
               'cands': cands, 'seqs': seqs, 'lib': len(lib)},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'  采样 {len(samples)} 帧, 候选 {len(cands)} 条 -> {out}', flush=True)
    for c in cands[:15]:
        print(f'    {c["t"]} [{c["text"]}]', flush=True)
    return cands, {'intervals': len(intervals), 'samples': len(samples), 'cands': len(cands)}


def main():
    eps = sys.argv[1:] or [f'P{i:02d}' for i in range(1, 26)]
    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH,
        # 固定 rec 输入宽度与 batch=1: 彻底消除 CUDA 首次执行慢帧(浮动 shape)
        # 1536 = 32:1 宽比上限, 兼容单行 30 字; 实测稳定 ~0.6s/帧
        'Rec.rec_img_shape': [3, 48, 1536],
        'Rec.rec_batch_num': 1,
    })
    print('OCR 就绪', flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    for ep in eps:
        scan_episode(ep, ocr)


if __name__ == '__main__':
    main()
