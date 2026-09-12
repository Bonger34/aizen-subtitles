# -*- coding: utf-8 -*-
"""对"疑似漏句台词"逐条到视频复核, 通过后补入库(条目 + 配图帧)。

复核: 在候选秒 ±0.4s 取 3 帧, 用 y895~1045 裁剪 OCR; 候选文本字符需 >=80% 出现在 OCR 结果里。
去重: 库中 ±3s 已有同文本, 或全库已有等价文本 -> 跳过。
入库: 抽该秒画面存为 {集}_{时刻}.jpg, subtitle_clean 追加条目。

用法: python dense3_apply.py [--apply] [--limit N]
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
SRC = os.path.join(B, 'review', 'dense3_dialogue.json')
OUT = os.path.join(B, 'review', 'dense3_verified.json')


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def ts_of(s):
    return f'{int(s) // 60}m{int(s) % 60:02d}s'


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def main():
    apply = '--apply' in sys.argv
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 0
    cands = json.load(open(SRC, encoding='utf-8'))
    if limit:
        cands = cands[:limit]
    # 库
    lib, allt = {}, []
    for fn in sorted(os.listdir(CLEAN)):
        if fn.endswith('.json'):
            ep = fn[1:4]
            lib[ep] = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
            allt += [cn(e.get('text')) for e in lib[ep]]

    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
    })
    caps, files = {}, set(os.listdir(FR))
    verified, skipped = [], []
    for i, c in enumerate(cands):
        if i % 50 == 0:
            print(f'  {i}/{len(cands)}', flush=True)
        ep, sec, want = c['ep'], c['sec'], cn(c['text'])
        if want in allt:                       # 全库已有等价文本
            skipped.append({**c, 'why': '全库已有'})
            continue
        if ep not in caps:
            caps[ep] = cv2.VideoCapture(find_video(ep))
        cap = caps[ep]
        fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
        got, bestd = '', None
        for d in (0.0, -0.4, 0.4):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((sec + d) * fps)))
            ok, fr = cap.read()
            if not ok:
                continue
            h, w = fr.shape[:2]
            sy = h / 1080.0
            cc = fr[int(895 * sy):int(1045 * sy), int(100 * (w / 1920.0)):int(1820 * (w / 1920.0))]
            cc = cv2.resize(cc, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
            arr = cc.copy()
            mk = np.all(arr > 245, axis=2)
            arr[mk] = [255, 255, 255]
            arr[~mk] = [0, 0, 0]
            r = ocr(arr)
            t = cn(''.join(r.txts) if r.txts else '')
            cont = sum(1 for ch in want if ch in t) / len(want)
            if cont >= 0.8 and (bestd is None or d == 0.0):
                got, bestd = t, d
            if got and bestd == 0.0:
                break
        if not got:
            skipped.append({**c, 'why': '画面未复核通过'})
            continue
        verified.append({**c, 'ocr': got, 'delta': bestd})
        if apply:
            # 与库中 ±3s 同文本去重
            near_same = [e for e in lib[ep]
                         if cn(e.get('text')) == want and abs(sec_of(e['timestamp']) - sec) <= 3]
            if near_same:
                skipped.append({**c, 'why': '±3s 已有同文本'})
                continue
            taken = {sec_of(e['timestamp']) for e in lib[ep]}
            s = sec
            name = f'{ep}_{ts_of(s)}.jpg'
            while s in taken or name in files:
                s += 1
                name = f'{ep}_{ts_of(s)}.jpg'
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((sec + bestd) * fps)))
            ok, fr = cap.read()
            if ok:
                cv2.imwrite(os.path.join(FR, name),
                            cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                            [cv2.IMWRITE_JPEG_QUALITY, 90])
                files.add(name)
                lib[ep].append({'timestamp': ts_of(s), 'similarity': 0.0, 'text': c['text']})
                lib[ep].sort(key=lambda e: sec_of(e['timestamp']))
                p = [os.path.join(CLEAN, f) for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
                json.dump(lib[ep], open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                allt.append(want)
    for c in caps.values():
        c.release()
    json.dump({'verified': verified, 'skipped': skipped}, open(OUT, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    lines = [f'复核结果: 通过 {len(verified)} / 跳过 {len(skipped)}' + ('(已入库)' if apply else '(预演)')]
    for v in verified[:80]:
        lines.append(f"  {v['ep']} {v['t']:>7s} [{v['text']}]  画面=[{v['ocr']}]")
    txt = '\n'.join(lines)
    open(os.path.join(B, 'review', 'dense3_verify.txt'), 'w', encoding='utf-8').write(txt)
    print(txt[:6000])


if __name__ == '__main__':
    main()
