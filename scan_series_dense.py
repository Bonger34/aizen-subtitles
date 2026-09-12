# -*- coding: utf-8 -*-
"""全系列密集扫描(扩窗 + 0.25s 密采): 找出库里没有的台词。

区间来源: 复用 review/ext_regions/{ep}.json 的三区域检测结果
          = 字幕带 BAND(895-985) ∪ 带下方 LOW(985-1062), 两路任一触发即算字幕区间。
采样密度: 区间内每 0.25s 一帧(比当年 0.35s 更密)。
OCR 裁剪: y 878~1075(覆盖标准位置与偏低位置), 二值化 >245。
状态去重: 对二值化后的裁剪做像素比对, 与"上次已 OCR 的那一张"一致度 >= 0.985 则跳过 OCR
          —— 密采样但只对"字幕变过"的时刻做 OCR, 用密度换召回、不用算力换。
判定: 与库 ±5s 内条目比包含度, < 0.6 视为候选(库里没有)。

输出: review/dense2/{ep}.json(候选) + review/dense2_frames/*.jpg(候选帧, 供复核)
      每集跑完立即写盘。
用法: python scan_series_dense.py [P01 P02 ...]
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
EXT = os.path.join(B, 'review', 'ext_regions')
OUTD = os.path.join(B, 'review', 'dense2')
FD = os.path.join(B, 'review', 'dense2_frames')
os.makedirs(OUTD, exist_ok=True)
os.makedirs(FD, exist_ok=True)
CROP = (100, 878, 1820, 1075)
STEP = 0.25
SAME = 0.985          # 二值化裁剪一致度阈值(>= 视为同一字幕状态, 跳过 OCR)
LIB_WIN, BEF_TAU = 5, 0.6


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def sec_of(t):
    m = re.match(r'(\d+)m(\d+)s', t)
    return int(m.group(1)) * 60 + int(m.group(2))


def ts_of(s):
    return f'{int(s) // 60}m{int(s) % 60:02d}s'


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def load_lib(ep):
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    return [(sec_of(e['timestamp']), norm(e.get('text'))) for e in
            json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))]


def merge_ivs(ivs):
    """把秒区间列表合并(重叠/相邻的合成一段)。"""
    out = []
    for a, b in sorted((x[0], x[1]) for x in ivs):
        if out and a <= out[-1][1] + 0.3:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def main():
    eps = sys.argv[1:] or [f'P{i:02d}' for i in range(1, 26)]
    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
    })
    print('OCR 就绪', flush=True)
    for ep in eps:
        jf = os.path.join(EXT, f'{ep}.json')
        if not os.path.exists(jf):
            print(f'{ep}: 缺区间文件, 跳过', flush=True)
            continue
        d = json.load(open(jf, encoding='utf-8'))
        ivs = merge_ivs(d['regions']['BAND'] + d['regions']['LOW'])
        lib = load_lib(ep)
        cap = cv2.VideoCapture(find_video(ep))
        fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # 采样帧号集合
        want = set()
        for a, b in ivs:
            f0, f1 = int(a * fps), min(total - 1, int(b * fps))
            n = f0
            while n <= f1:
                want.add(n)
                n += max(1, int(round(STEP * fps)))
        n, occ, cands, samples, ocred = 0, 0, [], 0, 0
        last = None
        for f in sorted(want):
            # n = 已消费的帧数(= 下一个待取帧号)。抓到 n == f+1 时, 最后一次 grab 得到的正是第 f 帧。
            while n <= f:
                if not cap.grab():
                    break
                n += 1
            ok, fr = cap.retrieve()
            if not ok:
                continue
            h, w = fr.shape[:2]
            sy = h / 1080.0
            c = fr[int(CROP[1] * sy):int(CROP[3] * sy), int(CROP[0] * (w / 1920.0)):int(CROP[2] * (w / 1920.0))]
            arr = c.copy()
            mk = np.all(arr > 245, axis=2)
            arr[mk] = [255, 255, 255]
            arr[~mk] = [0, 0, 0]
            binm = (arr[:, :, 0] > 128)
            samples += 1
            if last is not None and binm.shape == last.shape:
                agree = float((binm == last).mean())
                if agree >= SAME:
                    continue
            last = binm
            ocred += 1
            try:
                r = ocr(arr)
                t = norm(''.join(r.txts) if r.txts else '')
            except Exception:
                t = ''
            if len(t) < 2:
                continue
            sec = int(round(f / fps))
            win = [lx for lt, lx in lib if abs(lt - sec) <= LIB_WIN]
            bef = max((sum(1 for ch in t if ch in x) / len(t) for x in win), default=0.0)
            if bef < BEF_TAU:
                name = f'{ep}_{ts_of(sec)}s.jpg'
                k = 1
                while os.path.exists(os.path.join(FD, name)):
                    name = f'{ep}_{ts_of(sec)}s_{k}.jpg'
                    k += 1
                cv2.imwrite(os.path.join(FD, name),
                            cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                            [cv2.IMWRITE_JPEG_QUALITY, 90])
                cands.append({'t': ts_of(sec), 'sec': sec, 'text': t, 'bef': round(bef, 2),
                              'frame': name})
        cap.release()
        json.dump({'ep': ep, 'intervals': len(ivs), 'samples': samples, 'ocr': ocred,
                   'cands': cands}, open(os.path.join(OUTD, f'{ep}.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(f'{ep}: 区间 {len(ivs)}, 采样 {samples}, 实 OCR {ocred}, 候选 {len(cands)}', flush=True)
        for c in cands[:5]:
            print(f"     {c['t']} [{c['text']}] (bef={c['bef']})", flush=True)


if __name__ == '__main__':
    main()
