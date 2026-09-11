# -*- coding: utf-8 -*-
"""修复"共用配图": 为出错条目补抽它自己那句话的帧。

单趟顺序读帧(不用 cap.set 跳转), 对每条目在 ts±WIN 秒内**逐 0.5 秒**取画面,
裁剪 y880-1050 后分别用 >245 / >235 两种二值化各 OCR 一次, 取包含度最高者。
包含度 >= 0.8 视为找到; 落盘为新帧(绝不覆盖正被其他条目使用的文件)并改指向。

用法:
  python fix_shared_frames2.py            # 预演
  python fix_shared_frames2.py --apply
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
FR = os.path.join(B, 'Web', 'frames')
FMAP = os.path.join(B, 'Web', 'frames_map.js')
SRC = os.path.join(B, 'review', 'shared_frames_ocr.json')
OUT = os.path.join(B, 'review', 'shared_fix_result.json')
BAND = (100, 880, 1820, 1050)
WIN = float(os.environ.get('FIX_WIN', '10'))
SUB = 0.5
TAU = 0.8


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9]', s or ''))


def sec(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2))


def ts_of(s):
    return f'{int(s) // 60}m{int(s) % 60:02d}s'


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def build_targets():
    rows = json.load(open(SRC, encoding='utf-8'))
    tg = []
    for r in rows:
        ep = r['frame'][:3]
        e, v = r['entries'], r['verdict']
        if '后一条配图错' in v:
            idxs = [1]
        elif '前一条配图错' in v:
            idxs = [0]
        elif '都对不上' in v:
            idxs = [0, 1]
        else:
            continue
        for i in idxs:
            ts, tx = e[i]
            tg.append({'ep': ep, 'ts': ts, 'sec': sec(ts), 'text': tx, 'old': r['frame']})
    return tg


def crop_for(frame):
    h, w = frame.shape[:2]
    sy = h / 1080.0
    c = frame[int(BAND[1] * sy):int(BAND[3] * sy),
              int(BAND[0] * (w / 1920.0)):int(BAND[2] * (w / 1920.0))]
    return cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)


def main():
    targets = build_targets()
    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
    })
    print(f'目标 {len(targets)} 条, 窗口 ±{WIN}s 步长 {SUB}s, 双阈值(245/235)', flush=True)

    best = {}          # idx -> (sec, score, ocr)
    keep = {}          # idx -> 960x540 图像
    by_ep = {}
    for i, t in enumerate(targets):
        by_ep.setdefault(t['ep'], []).append((i, t))

    for ep, items in sorted(by_ep.items()):
        cap = cv2.VideoCapture(find_video(ep))
        fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
        dur = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
        want = {}
        for i, t in items:
            d = -WIN
            while d <= WIN + 1e-9:
                s = t['sec'] + d
                if 0 <= s <= dur:
                    want.setdefault(int(round(s * fps)), []).append((i, t, s))
                d += SUB
        order = sorted(want)
        n, ti = 0, 0
        while ti < len(order):
            if not cap.grab():
                break
            n += 1
            if n - 1 >= order[ti]:
                ok, frame = cap.retrieve()
                if ok:
                    crop = crop_for(frame)
                    small = None
                    for i, t, s in want[order[ti]]:
                        want_t = norm(t['text'])
                        if not want_t:
                            continue
                        sc_best, got_best = -1.0, ''
                        for th in (245, 235):
                            arr = crop.copy()
                            mk = np.all(arr > th, axis=2)
                            arr[mk] = [255, 255, 255]
                            arr[~mk] = [0, 0, 0]
                            try:
                                rr = ocr(arr)
                                got = norm(''.join(rr.txts) if rr.txts else '')
                            except Exception:
                                got = ''
                            sc = sum(1 for ch in want_t if ch in got) / len(want_t)
                            if sc > sc_best:
                                sc_best, got_best = sc, got
                        if i not in best or sc_best > best[i][1]:
                            best[i] = (s, round(sc_best, 2), got_best)
                            if small is None:
                                small = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
                            keep[i] = small
                ti += 1
        cap.release()
        done = sum(1 for i, t in items if best.get(i, (0, 0, ''))[1] >= TAU)
        print(f'  {ep}: {len(items)} 条, 达标 {done}', flush=True)

    apply = '--apply' in sys.argv
    MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;', open(FMAP, encoding='utf-8').read(), re.S).group(1))
    files = set(os.listdir(FR))
    ok_list, bad_list = [], []
    for i, t in enumerate(targets):
        b = best.get(i)
        full = [k for k in MAP if k.startswith(f"[{t['ep']}]") and k.endswith('|' + t['ts'])]
        if not b or b[1] < TAU or not full or i not in keep:
            bad_list.append({'ep': t['ep'], 'ts': t['ts'], 'text': t['text'], 'old': t['old'],
                             'best_sec': ts_of(b[0]) if b else None, 'best_score': b[1] if b else None,
                             'best_ocr': b[2] if b else None})
            continue
        name = f"{t['ep']}_{t['ts']}.jpg"
        if name in files:
            name = f"{t['ep']}_{t['ts']}_fix.jpg"
        if apply:
            cv2.imwrite(os.path.join(FR, name), keep[i], [cv2.IMWRITE_JPEG_QUALITY, 90])
            files.add(name)
            for k in full:
                MAP[k] = name
        ok_list.append({'ep': t['ep'], 'ts': t['ts'], 'text': t['text'], 'old': t['old'],
                        'new': name, 'found_at': ts_of(b[0]), 'delta': round(b[0] - t['sec'], 1),
                        'score': b[1], 'ocr': b[2]})
    if apply:
        open(FMAP, 'w', encoding='utf-8').write('window.FRAMES_MAP = ' +
                                                json.dumps(MAP, ensure_ascii=False) + ';')
        json.dump({'ok': ok_list, 'bad': bad_list}, open(OUT, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)

    lines = [f'共用配图修复: 修好 {len(ok_list)} / 未解决 {len(bad_list)}' + ('(已落盘)' if apply else '(预演)')]
    import collections
    dist = collections.Counter(int(round(r['delta'])) for r in ok_list)
    lines.append(f'  命中位置相对原时间戳的偏移分布: {dict(sorted(dist.items()))}')
    for r in ok_list[:60]:
        lines.append(f"  {r['ep']} {r['ts']:>7s} ({r['delta']:+4.1f}s, 分{r['score']}) [{r['text'][:20]:22s}] -> {r['new']}")
    for r in bad_list:
        lines.append(f"  !! {r['ep']} {r['ts']:>7s} [{r['text'][:20]}] 未找到 最佳={r['best_sec']} 分={r['best_score']} ocr=[{(r['best_ocr'] or '')[:40]}]")
    txt = '\n'.join(lines)
    open(os.path.join(B, 'review', 'shared_fix_report.txt'), 'w', encoding='utf-8').write(txt)
    print(txt[:4000])


if __name__ == '__main__':
    main()
