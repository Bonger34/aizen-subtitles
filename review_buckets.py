# -*- coding: utf-8 -*-
"""把未人工复核的两个桶(短文本 198 / 噪声 936)逐条到视频复核, 看是否藏有真台词。

判据: 候选文本在候选秒 ±0.4s 内的画面 OCR 中 >=80% 复现, 且全库没有等价文本 -> 真漏句。
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
FR = os.path.join(B, 'Web', 'frames')
D2 = os.path.join(B, 'review', 'dense2')


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def strip_digits(s):
    return re.sub(r'\d+$', '', re.sub(r'^\d+', '', s))


def score(a, b):
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return min(sum(1 for ch in a if ch in sb) / len(a), sum(1 for ch in b if ch in sa) / len(b))


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def ts_of(s):
    return f'{s // 60}m{s % 60:02d}s'


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


apply = '--apply' in sys.argv
lib, allt = {}, []
for fn in sorted(os.listdir(CLEAN)):
    if fn.endswith('.json'):
        title = fn[:-5]
        lib[title] = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
        allt += [cn(e.get('text')) for e in lib[title]]
files = set(os.listdir(FR))

# 收集两个桶的全部候选(带 sec)
pool = []
for f in sorted(os.listdir(D2)):
    if not f.endswith('.json'):
        continue
    d = json.load(open(os.path.join(D2, f), encoding='utf-8'))
    ep = d['ep']
    for c in d['cands']:
        t = strip_digits(cn(c['text']))
        noise = (len(t) < 2) or (len(re.sub(r'[^0-9]', '', t)) / max(1, len(t)) > 0.34)
        pool.append({'ep': ep, 'sec': c['sec'], 't': c['t'], 'text': t, 'noisy': noise})
print('候选池', len(pool))

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
caps, hits = {}, []
for i, c in enumerate(pool):
    t = c['text']
    if len(t) < 1:
        continue
    if any(score(t, lt) >= 0.8 for lt in allt if abs(len(lt) - len(t)) <= 4):
        continue                                    # 全库已有等价文本
    ep, sec = c['ep'], c['sec']
    if ep not in caps:
        caps[ep] = cv2.VideoCapture(find_video(ep))
    cap = caps[ep]
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    got, delta = '', 0.0
    for dd in (0.0, -0.4, 0.4):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((sec + dd) * fps)))
        r, fr = cap.read()
        if not r:
            continue
        h, w = fr.shape[:2]
        sy = h / 1080.0
        cc = fr[int(895 * sy):int(1045 * sy), int(100 * (w / 1920.0)):int(1820 * (w / 1920.0))]
        cc = cv2.resize(cc, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
        arr = cc.copy()
        mk = np.all(arr > 245, axis=2)
        arr[mk] = [255, 255, 255]
        arr[~mk] = [0, 0, 0]
        rr = ocr(arr)
        g = cn(''.join(rr.txts) if rr.txts else '')
        if sum(1 for ch in t if ch in g) / len(t) >= 0.8:
            got, delta = g, dd
            break
    if not got:
        continue
    # 画面复现了: 再看画面文本是否其实已在库中(避免把碎片当新句)
    if any(score(cn(got), lt) >= 0.8 for lt in allt if abs(len(lt) - len(cn(got))) <= 6):
        continue
    hits.append({**c, 'ocr': got, 'delta': delta})
    print(f"  {ep} {c['t']}  [{t}]  画面=[{got}]", flush=True)
    if apply:
        title = [k for k in lib if k.startswith(f'[{ep}]')][0]
        data = lib[title]
        taken = {sec_of(e['timestamp']) for e in data}
        s = sec
        name = f'{ep}_{ts_of(s)}.jpg'
        while s in taken or name in files:
            s += 1
            name = f'{ep}_{ts_of(s)}.jpg'
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((sec + delta) * fps)))
        r, fr = cap.read()
        if r:
            cv2.imwrite(os.path.join(FR, name),
                        cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])
            files.add(name)
        data.append({'timestamp': ts_of(s), 'similarity': 0.0, 'text': c['text']})
        data.sort(key=lambda e: sec_of(e['timestamp']))
        json.dump(data, open(os.path.join(CLEAN, title + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        allt.append(cn(c['text']))
for cap in caps.values():
    cap.release()
print(f'复核发现真漏句 {len(hits)} 条' + ('(已入库)' if apply else '(预演)'))
