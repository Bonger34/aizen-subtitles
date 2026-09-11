# -*- coding: utf-8 -*-
"""共用配图修复(定稿版): 给出错条目补抽它自己那句话的帧。

首轮全网格结果的偏移分布(107 条): 0s 66 / +1s 21 / -1s 10 / ±2~4s 10 / -7s,-10s 3,
所以候选位置按 |偏移| 从小到大枚举, 一旦 OCR 包含度 >=0.8 立即停止。

关于取帧方式: 这里用 cap.set(POS_FRAMES) 定位 + 读帧, 与项目"顺序读帧"的铁律不同,
但本脚本的**采纳判据是画面内容**(OCR 必须与条目文本匹配 >=0.8), 定位若不准只会得到
低分并被跳过, 因此不存在之前 seek 静默错帧导致误采纳的风险。

每处理完一条立即写盘, 中途中断不丢结果。
用法: python fix_shared_frames3.py [--apply]
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
PROG = os.path.join(B, 'review', 'shared_fix3_progress.json')
BAND = (100, 880, 1820, 1050)
TAU = 0.8
MAXOFF = 10.0


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
        ep, e, v = r['frame'][:3], r['entries'], r['verdict']
        idxs = [1] if '后一条配图错' in v else [0] if '前一条配图错' in v else [0, 1] if '都对不上' in v else []
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


def offsets():
    out = [0.0]
    d = 0.5
    while d <= MAXOFF + 1e-9:
        out += [-d, d]
        d += 0.5
    return out


def main():
    apply = '--apply' in sys.argv
    targets = build_targets()
    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
    })
    MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;', open(FMAP, encoding='utf-8').read(), re.S).group(1))
    files = set(os.listdir(FR))
    done = json.load(open(PROG, encoding='utf-8')) if os.path.exists(PROG) else {}
    offs = offsets()
    print(f'目标 {len(targets)} 条, 已处理 {len(done)}', flush=True)

    for ep in sorted({t['ep'] for t in targets}):
        todo = [t for t in targets if t['ep'] == ep and f"{t['ep']}|{t['ts']}" not in done]
        if not todo:
            continue
        cap = cv2.VideoCapture(find_video(ep))
        fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
        dur = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
        for t in todo:
            want = norm(t['text'])
            best = None
            for off in offs:
                s = t['sec'] + off
                if s < 0 or s > dur:
                    continue
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(s * fps)))
                ok, frame = cap.read()
                if not ok:
                    continue
                crop = crop_for(frame)
                sc, got = -1.0, ''
                for th in (245, 235):
                    arr = crop.copy()
                    mk = np.all(arr > th, axis=2)
                    arr[mk] = [255, 255, 255]
                    arr[~mk] = [0, 0, 0]
                    try:
                        rr = ocr(arr)
                        g = norm(''.join(rr.txts) if rr.txts else '')
                    except Exception:
                        g = ''
                    v = sum(1 for ch in want if ch in g) / len(want) if want else 0.0
                    if v > sc:
                        sc, got = v, g
                if best is None or sc > best[1]:
                    best = (s, round(sc, 2), got, frame.copy())
                if sc >= TAU:
                    break
            key = f"{t['ep']}|{t['ts']}"
            rec = {'ep': t['ep'], 'ts': t['ts'], 'text': t['text'], 'old': t['old'],
                   'found_at': ts_of(best[0]) if best else None,
                   'delta': round(best[0] - t['sec'], 1) if best else None,
                   'score': best[1] if best else None, 'ocr': best[2] if best else None}
            if best and best[1] >= TAU and apply:
                name = f"{t['ep']}_{t['ts']}.jpg"
                if name in files:
                    name = f"{t['ep']}_{t['ts']}_fix.jpg"
                cv2.imwrite(os.path.join(FR, name),
                            cv2.resize(best[3], (960, 540), interpolation=cv2.INTER_AREA),
                            [cv2.IMWRITE_JPEG_QUALITY, 90])
                files.add(name)
                for k in [k for k in MAP if k.startswith(f"[{t['ep']}]") and k.endswith('|' + t['ts'])]:
                    MAP[k] = name
                rec['new'] = name
            done[key] = rec
            json.dump(done, open(PROG, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        cap.release()
        n_ok = sum(1 for k, v in done.items() if k.startswith(ep + '|') and (v.get('score') or 0) >= TAU)
        print(f'  {ep}: 累计达标 {n_ok}', flush=True)
        if apply:
            open(FMAP, 'w', encoding='utf-8').write('window.FRAMES_MAP = ' +
                                                    json.dumps(MAP, ensure_ascii=False) + ';')
    if apply:
        open(FMAP, 'w', encoding='utf-8').write('window.FRAMES_MAP = ' +
                                                json.dumps(MAP, ensure_ascii=False) + ';')
    ok = [v for v in done.values() if (v.get('score') or 0) >= TAU]
    bad = [v for v in done.values() if (v.get('score') or 0) < TAU]
    import collections
    dist = collections.Counter(v['delta'] for v in ok)
    lines = [f'共用配图修复: 达标 {len(ok)} / 未达标 {len(bad)}' + ('(已落盘)' if apply else '(预演)'),
             f'  命中偏移分布: {dict(sorted(dist.items(), key=lambda x: (x[0] is None, x[0])))}']
    for v in bad:
        lines.append(f"  !! {v['ep']} {v['ts']:>7s} [{v['text'][:20]}] 最佳 {v['found_at']} 分 {v['score']} ocr=[{(v['ocr'] or '')[:36]}]")
    txt = '\n'.join(lines)
    open(os.path.join(B, 'review', 'shared_fix3_report.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
