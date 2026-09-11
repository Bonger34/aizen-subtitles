# -*- coding: utf-8 -*-
"""对"仅 LOW 区间"(现有字幕带完全没覆盖、只有带下方有白字)做采样 OCR, 找漏掉的台词。

流程与 scan_cont.py 一致, 只有两点不同:
  1. 只在 仅LOW 区间内采样(每个区间每 0.35s 一帧, 顺序读帧不跳帧);
  2. OCR 的裁剪区扩大到 y 850~1062(标准字幕带 + 下方), 二值化阈值仍为 >245。

输出 review/ext_cands.json: 未能在库中匹配到的新文本候选(含帧图路径)。
用法: python scan_ext_ocr.py [P01 P02 ...]
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
EXT = os.path.join(B, 'review', 'ext_regions')
OUTJSON = os.path.join(B, 'review', 'ext_cands.json')
CROP = (100, 850, 1820, 1062)     # 扩大的裁剪区(x0,y0,x1,y1, 1920x1080)
STEP = 0.35                       # 区间内采样间隔(秒)
LIB_WIN = 5
BEF_TAU = 0.6


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def load_lib(ep):
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    rows = []
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        m = re.match(r'(\d+)m(\d+)s', e.get('timestamp') or '')
        t = norm(e.get('text'))
        if m and t:
            rows.append((int(m.group(1)) * 60 + int(m.group(2)), t))
    return rows


def binarize(crop):
    arr = crop.copy()
    m = np.all(arr > 245, axis=2)
    arr[m] = [255, 255, 255]
    arr[~m] = [0, 0, 0]
    return arr


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def main():
    eps = sys.argv[1:] or [f'P{i:02d}' for i in range(1, 26)]
    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH,
        'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
    })
    print('OCR 就绪', flush=True)
    out = {}
    for ep in eps:
        jf = os.path.join(EXT, f'{ep}.json')
        if not os.path.exists(jf):
            print(f'{ep}: 无区间文件, 跳过', flush=True)
            continue
        ivs = json.load(open(jf, encoding='utf-8'))['low_only']
        if not ivs:
            print(f'{ep}: 无 仅LOW 区间', flush=True)
            continue
        lib = load_lib(ep)
        cap = cv2.VideoCapture(find_video(ep))
        fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # 需要处理的帧号 -> (秒, 区间序号)
        want, fidx = {}, 0
        for i, (s, e, _) in enumerate(ivs):
            t = s
            while t <= e:
                f = min(total - 1, int(round(t * fps)))
                want.setdefault(f, (t, i))
                t += STEP
        n = 0
        got = []
        for f in sorted(want):
            while n < f:
                if not cap.grab():
                    break
                n += 1
            ret, frame = cap.retrieve()
            n += 1
            if not ret:
                continue
            t, i = want[f]
            crop = frame[CROP[1]:CROP[3], CROP[0]:CROP[2]]
            try:
                res = ocr(binarize(crop))
            except Exception as ex:
                print(f'  OCR err {ep} f{f}: {ex}', flush=True)
                continue
            raw = ''.join(res.txts) if res.txts else ''
            tn = norm(raw)
            if len(tn) < 2:
                continue
            sec = int(round(t))
            win = [lt for ts, lt in lib if abs(ts - sec) <= LIB_WIN]
            bef = max((sum(1 for c in tn if c in w) / len(tn) for w in win), default=0.0)
            got.append({'t': f'{sec // 60}m{sec % 60:02d}s', 'sec': sec, 'int': i,
                        'text': tn, 'raw': raw, 'bef': round(bef, 3), 'fidx': f})
        cap.release()
        # 同一区间内相邻重复文本去重
        uniq, prev = [], {}
        for g in got:
            last = prev.get(g['int'])
            if last and (g['text'] == last or (len(g['text']) >= 2 and g['text'] in last)):
                continue
            prev[g['int']] = g['text']
            uniq.append(g)
        cands = [g for g in uniq if g['bef'] < BEF_TAU]
        out[ep] = {'intervals': len(ivs), 'samples': len(got), 'uniq': len(uniq),
                   'cands': cands, 'all': uniq}
        print(f'{ep}: 区间 {len(ivs)}, 采样 {len(got)}, 去重 {len(uniq)}, 候选 {len(cands)}', flush=True)
        for c in cands[:10]:
            print(f"    {c['t']} [{c['text']}] (bef={c['bef']})", flush=True)
        json.dump(out, open(OUTJSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('写出', OUTJSON)


if __name__ == '__main__':
    main()
