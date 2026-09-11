# -*- coding: utf-8 -*-
"""对 9 条未解决目标做密集扫描: 0.25s 步长 × ±8s, 双阈值, 两种裁剪(字幕带 / 整下半屏)。

不止比对条目文本, 也记录该处"最像中文台词"的读法 —— 因为其中多条库文本本身就是碎片
(如「重」「口」「金」「敬告」), 真正的修复可能是改文本而不是改配图。
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
PROG = os.path.join(B, 'review', 'shared_fix3_progress.json')
OUT = os.path.join(B, 'review', 'shared_residue.txt')
CROPS = {'band': (100, 880, 1820, 1050), 'lower': (100, 700, 1820, 1075)}
STEP, WIN = 0.25, 8.0


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def crop_for(frame, box):
    h, w = frame.shape[:2]
    sy = h / 1080.0
    c = frame[int(box[1] * sy):int(box[3] * sy), int(box[0] * (w / 1920.0)):int(box[2] * (w / 1920.0))]
    return cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)


def main():
    prog = json.load(open(PROG, encoding='utf-8'))
    todo = [v for v in prog.values() if (v.get('score') or 0) < 0.8]
    print(f'未解决 {len(todo)} 条, 开始密集扫描', flush=True)
    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
    })
    lines = ['未解决目标的密集扫描(0.25s × ±8s, 双阈值, 带内/下半屏两种裁剪)', '']
    for v in todo:
        ep = v['ep']
        sec = int(v['ts'].split('m')[0]) * 60 + int(v['ts'].split('m')[1].rstrip('s'))
        cap = cv2.VideoCapture(find_video(ep))
        fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
        want = norm(v['text'])
        rows = []
        d = -WIN
        while d <= WIN + 1e-9:
            s = sec + d
            if s >= 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(s * fps)))
                ok, frame = cap.read()
                if ok:
                    for cname, box in CROPS.items():
                        cr = crop_for(frame, box)
                        for th in (245, 235):
                            arr = cr.copy()
                            mk = np.all(arr > th, axis=2)
                            arr[mk] = [255, 255, 255]
                            arr[~mk] = [0, 0, 0]
                            try:
                                rr = ocr(arr)
                                got = norm(''.join(rr.txts) if rr.txts else '')
                            except Exception:
                                got = ''
                            if len(got) < 2:
                                continue
                            sc = sum(1 for ch in want if ch in got) / len(want) if want else 0.0
                            rows.append((round(sc, 2), round(s, 2), cname, th, got))
            d += STEP
        cap.release()
        rows.sort(key=lambda x: (-x[0], -len(x[4])))
        lines.append(f"{ep} {v['ts']}  库文本=[{v['text']}]  (原配图={v['old']})")
        for sc, s, cname, th, got in rows[:6]:
            lines.append(f"     分{sc:4.2f} @{int(s)//60}m{int(s)%60:02d}s.{int((s%1)*100):02d} "
                         f"裁剪={cname} 阈值={th}  [{got}]")
        if not rows:
            lines.append('     (该时段各裁剪/阈值均未读出 >=2 字中文)')
        lines.append('')
    txt = '\n'.join(lines)
    open(OUT, 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
