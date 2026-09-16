# -*- coding: utf-8 -*-
"""孤儿帧 OCR 复核:确认孤儿帧里的字幕是否已被库覆盖。

分组:
  C 组 same 非空(该秒库内已有条目) -> 直接判定已覆盖
  B 组 仅 ±2s 内有条目            -> 抽样 OCR, 与本行邻近条目比对
  A 组 ±2s 内全无条目             -> 全量 OCR, 与 ±8s 窗口比对(沿用 0.6 包含度判据)

用法:
  python orphan_ocr.py probe        # 阈值探测(30 帧)
  python orphan_ocr.py run [N_B]    # 全量 A + 抽样 N_B 条 B
"""
import os
import re
import sys
import json
import random

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

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FRAMES = os.path.join(BASE, 'docs', 'frames')
CLEAN = os.path.join(BASE, 'subtitle_clean')
SCAN = os.path.join(BASE, 'review', 'orphan_scan.json')
OUT = os.path.join(BASE, 'review', 'orphan_ocr.json')
AREA = (100, 895, 1820, 985)   # 1920x1080 坐标
LIB_WIN = 8
BEF_TAU = 0.6


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff]', s or ''))


def band(img):
    """从 960x540 帧裁字幕带, 2x 上采样回 1080p 尺度"""
    h, w = img.shape[:2]
    sx, sy = w / 1920.0, h / 1080.0
    x0, y0, x1, y1 = int(AREA[0] * sx), int(AREA[1] * sy), int(AREA[2] * sx), int(AREA[3] * sy)
    return cv2.resize(img[y0:y1, x0:x1], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)


def binarize(crop, th):
    arr = crop.copy()
    mask = np.all(arr > th, axis=2)
    arr[mask] = [255, 255, 255]
    arr[~mask] = [0, 0, 0]
    return arr


def load_lib():
    lib = {}
    for fn in os.listdir(CLEAN):
        m = re.match(r'\[P(\d+)\]', fn)
        if not m:
            continue
        ep = int(m.group(1))
        rows = []
        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
            mm = re.match(r'(\d+)m(\d+)s', e.get('timestamp') or '')
            t = norm(e.get('text'))
            if mm and t:
                rows.append((int(mm.group(1)) * 60 + int(mm.group(2)), t))
        lib[ep] = rows
    return lib


def make_ocr():
    return RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH,
        'Rec.rec_img_shape': [3, 48, 1536],
        'Rec.rec_batch_num': 1,
    })


def ocr_text(ocr, img):
    res = ocr(img)
    raw = ''.join(res.txts) if res.txts else ''
    return norm(raw), raw


def bef(tn, win):
    """OCR 文本对窗口内库条目的最大包含度"""
    if not tn or not win:
        return 0.0
    return max(sum(1 for c in tn if c in w) / len(tn) for w in win)


def probe():
    ocr = make_ocr()
    recs = json.load(open(SCAN, encoding='utf-8'))['recs']
    grpA = [r for r in recs if not r['same'] and not r['near']]
    sample = grpA[:30]
    print('帧            | th245        | th200        | 原图')
    for r in sample:
        img = cv2.imread(os.path.join(FRAMES, r['f']))
        if img is None:
            continue
        b = band(img)
        t245 = ocr_text(ocr, binarize(b, 245))[0]
        t200 = ocr_text(ocr, binarize(b, 200))[0]
        traw = ocr_text(ocr, b)[0]
        print(f"{r['f']:16s}| {t245:12s} | {t200:12s} | {traw}")


def run(n_b):
    ocr = make_ocr()
    print('OCR 就绪', flush=True)
    lib = load_lib()
    recs = json.load(open(SCAN, encoding='utf-8'))['recs']
    grpA = [r for r in recs if not r['same'] and not r['near']]
    grpB = [r for r in recs if not r['same'] and r['near']]
    grpC = [r for r in recs if r['same']]
    random.Random(11).shuffle(grpB)
    todo = grpA + grpB[:n_b]
    print(f'A组 {len(grpA)} 全量 / B组 {len(grpB)} 抽 {n_b} / C组 {len(grpC)} 跳过', flush=True)

    out = {'A': [], 'B': [], 'nA': len(grpA), 'nB': len(grpB), 'nC': len(grpC)}
    for i, r in enumerate(todo):
        if i % 25 == 0:
            print(f'  {i}/{len(todo)}', flush=True)
        img = cv2.imread(os.path.join(FRAMES, r['f']))
        if img is None:
            continue
        b = band(img)
        tn245, _ = ocr_text(ocr, binarize(b, 245))
        tn200, raw200 = ocr_text(ocr, binarize(b, 200))
        tn = tn200 if len(tn200) > len(tn245) else tn245
        rows = lib.get(r['ep'], [])
        win = [t for ts, t in rows if abs(ts - r['sec']) <= LIB_WIN]
        score = bef(tn, win)
        out['A' if r in grpA else 'B'].append({
            'f': r['f'], 'sec': r['sec'], 'wr': r['wr'], 'ocr': tn, 'ocr245': tn245,
            'raw': raw200, 'near': r['near'], 'bef': round(score, 3),
            'hit': score >= BEF_TAU, 'short': len(tn) < 2,
        })
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    lines = []
    for tag in ('A', 'B'):
        rs = out[tag]
        if not rs:
            continue
        hit = sum(1 for x in rs if x['hit'])
        short = sum(1 for x in rs if x['short'])
        miss = [x for x in rs if not x['hit'] and not x['short']]
        head = f'=== {tag} 组 {len(rs)} 帧:命中库 {hit} / 空或单字 {short} / 未命中 {len(miss)} ==='
        print(head, flush=True)
        lines.append(head)
        for x in miss:
            row = f"  {x['f']:16s} wr={x['wr']:.3f} ocr=[{x['ocr']}] near={x['near'][:2]} bef={x['bef']}"
            print(row, flush=True)
            lines.append(row)
    with open(os.path.join(BASE, 'review', 'orphan_ocr_report.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('写出', OUT, flush=True)


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if mode == 'probe':
        probe()
    else:
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 250)
