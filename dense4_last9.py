# -*- coding: utf-8 -*-
"""收尾: 对 9 条正片残留台词候选逐条到视频复核, 确认后入库。"""
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
FR = os.path.join(B, 'docs', 'frames')
CANDS = [('P04', '10m38s', '逗你的我开玩笑的'), ('P07', '11m33s', '想到这'),
         ('P08', '16m02s', '十分常见的情形'), ('P10', '8m56s', '能守护他们笑容的'),
         ('P13', '5m32s', '但我还是很想知道'), ('P17', '3m49s', '还有点扎手呢'),
         ('P18', '3m08s', '真是奇怪'), ('P18', '22m16s', '整座城市得救了'),
         ('P22', '13m18s', '我们得想办法对付它')]


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def ts_of(s):
    return f'{s // 60}m{s % 60:02d}s'


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


apply = '--apply' in sys.argv
lib, files = {}, set(os.listdir(FR))
for fn in sorted(os.listdir(CLEAN)):
    if fn.endswith('.json'):
        lib[fn[:-5]] = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
alltexts = {cn(e.get('text')) for rows in lib.values() for e in rows}

ocr = RapidOCR(params={
    'EngineConfig.onnxruntime.use_cuda': True,
    'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
    'Det.lang': LangDet.MULTI,
    'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
    'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
})
caps = {}
for ep, ts, text in CANDS:
    want = cn(text)
    if want in alltexts:
        print(f'{ep} {ts} [{text}]  已存在, 跳过')
        continue
    if ep not in caps:
        caps[ep] = cv2.VideoCapture(find_video(ep))
    cap = caps[ep]
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    sec = sec_of(ts)
    got, delta = '', 0.0
    for dd in (0.0, -0.4, 0.4, -0.8, 0.8):
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
        t = cn(''.join(rr.txts) if rr.txts else '')
        if sum(1 for ch in want if ch in t) / len(want) >= 0.8:
            got, delta = t, dd
            break
    print(f"{ep} {ts} [{text}]  画面复核={'通过' if got else '未通过'}  OCR=[{got}]")
    if got and apply:
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
        data.append({'timestamp': ts_of(s), 'similarity': 0.0, 'text': text})
        data.sort(key=lambda e: sec_of(e['timestamp']))
        json.dump(data, open(os.path.join(CLEAN, title + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        alltexts.add(want)
for cap in caps.values():
    cap.release()
