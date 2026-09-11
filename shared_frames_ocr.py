# -*- coding: utf-8 -*-
"""对 119 组共用配图做 OCR 实测: 这张图到底是哪一条的画面?

对每组: OCR 共用帧 -> 与两条条目的文本各算包含度 -> 判定图的归属。
同时检查磁盘上是否已存在以"另一条时间戳"命名的帧(可直接改指向)。
"""
import json
import os
import re
import sys
import collections

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
FR = os.path.join(B, 'Web', 'frames')
CLEAN = os.path.join(B, 'subtitle_clean')
BAND = (100, 880, 1820, 1050)


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def sec(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2))


MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                           open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read(),
                           re.S).group(1))
text_of = {}
for fn in os.listdir(CLEAN):
    if fn.endswith('.json'):
        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
            text_of[f"{fn[:-5]}|{e['timestamp']}"] = e.get('text') or ''

rev = collections.defaultdict(list)
for k, v in MAP.items():
    rev[v].append(k)
groups = {f: sorted(ks, key=lambda k: sec(k.split('|')[1])) for f, ks in rev.items() if len(ks) > 1}

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
}) if False else RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
print('OCR 就绪, 组数', len(groups), flush=True)

files = set(os.listdir(FR))
res = collections.Counter()
rows = []
for i, (f, ks) in enumerate(sorted(groups.items())):
    if i % 20 == 0:
        print(f'  {i}/{len(groups)}', flush=True)
    img = cv2.imread(os.path.join(FR, f))
    if img is None:
        continue
    h, w = img.shape[:2]
    sy = h / 1080.0
    c = img[int(BAND[1] * sy):int(BAND[3] * sy), int(BAND[0] * (w / 1920.0)):int(BAND[2] * (w / 1920.0))]
    c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
    arr = c.copy()
    m = np.all(arr > 245, axis=2)
    arr[m] = [255, 255, 255]
    arr[~m] = [0, 0, 0]
    try:
        r = ocr(arr)
        t = norm(''.join(r.txts) if r.txts else '')
    except Exception:
        t = ''
    scores = []
    for k in ks:
        want = norm(text_of.get(k, ''))
        s = sum(1 for ch in want if ch in t) / len(want) if want else 0.0
        scores.append(round(s, 2))
    ok = [s >= 0.8 for s in scores]
    if all(ok):
        verdict = '两条都能对上(同屏两行/重复)'
    elif ok[0] and not ok[1]:
        verdict = '只对得上前一条 -> 后一条配图错'
    elif ok[1] and not ok[0]:
        verdict = '只对得上后一条 -> 前一条配图错'
    else:
        verdict = '两条都对不上'
    res[verdict] += 1
    ep = f[:3]
    alt = [f'{ep}_{k.split("|")[1]}.jpg' for k in ks]
    have_alt = [a for a in alt if a in files]
    rows.append({'frame': f, 'entries': [(k.split('|')[1], text_of.get(k, '')) for k in ks],
                 'ocr': t, 'scores': scores, 'verdict': verdict,
                 'existing_named_frames': sorted(set(have_alt))})

lines = ['共用配图归属实测(OCR 与两条条目文本各算包含度, >=0.8 视为对上):', '']
for k, v in res.most_common():
    lines.append(f'  {k}: {v}')
lines.append('')
for r in rows:
    lines.append(f"  {r['frame']}  [{r['verdict']}]  同图已有命名帧={r['existing_named_frames']}")
    for (ts, tx), sc in zip(r['entries'], r['scores']):
        lines.append(f'      {ts:>7s} 包含度={sc}  {tx}')
    lines.append(f"      OCR=[{r['ocr'][:60]}]")
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'shared_frames_ocr.txt'), 'w', encoding='utf-8').write(txt)
json.dump(rows, open(os.path.join(B, 'review', 'shared_frames_ocr.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n'.join(lines[:12]))
