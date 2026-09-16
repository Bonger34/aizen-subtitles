# -*- coding: utf-8 -*-
"""q_online.py — 单遍在线定位 + 重识别(替代 q_locate 的两遍扫描)。

原理:
  * 已存帧图与库文本一致(历史抽帧时用 OCR 校验过), 但帧图命名的时间戳不等于画面真实时刻
    —— 实测真实位置在 ts-3.2s ~ ts+0.9s 之间, 用 cap.set(POS_MSEC) 复现率仅 37%、单次 615ms;
  * 顺序 grab 全片只需 ~450fps(78s/集), 而 retrieve 一帧要 ~12ms —— 于是每 STEP 帧才取一次画面,
    用 64x36 灰度缩略图与帧图做模板匹配, 命中即对这张 1080p 原帧做宽裁剪双路识别;
  * 单遍完成, 不需要第二遍取帧。
用法: python q_online.py P01 [P02 ...] [--step 6] [--R 6] [--paths bin,raw]
输出: review/q_online_<EP>.json
"""
import json
import os
import re
import sys
import time

import cv2
import numpy as np

from q_common import (SCAN_TOP, SCAN_BOT, build_engine, sim, split_lines)
from q_rescan import rec_pair, tight_x, MIN_SEG_FILL, MIN_SEG_H, MAX_SEGS

B = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle_clean')
FR = os.path.join(B, 'docs', 'frames')
OUT_DIR = os.path.join(B, 'review')
SZ = (64, 36)
MAE_OK = 8.0        # 命中阈值(实测命中 0.2~6.0, 未命中 >7)
MAX_HITS = 4        # 每条目最多收集的命中帧(同一句字幕的连续帧 -> 天然投票)


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def load_map():
    s = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


def thumb(img):
    return cv2.cvtColor(cv2.resize(img, SZ, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)


def run_ep(ocr, ep, step=6, R=6.0, paths=('bin', 'raw')):
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]
    title = fn[:-5]
    data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
    MAP = load_map()
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    items = []
    for e in data:
        ts, sec = e.get('timestamp'), parse_ts(e.get('timestamp'))
        f = MAP.get(f'{title}|{ts}')
        ref = None
        if f:
            img = cv2.imread(os.path.join(FR, f))
            if img is not None:
                ref = thumb(img).astype(np.int16)
        items.append({'ts': ts, 'sec': sec, 'old': e.get('text', ''), 'frame': f, 'ref': ref,
                      'hits': [], 'n_cmp': 0, 'hits_n': 0})

    order = sorted([i for i, it in enumerate(items) if it['ref'] is not None and it['sec'] is not None],
                   key=lambda i: items[i]['sec'])
    los = {i: int(max(0, (items[i]['sec'] - R) * fps)) for i in order}
    his = {i: int((items[i]['sec'] + R) * fps) for i in order}

    t0 = time.time()
    t_ocr = 0.0
    n_rec = 0
    ptr, active = 0, []
    for n in range(total):
        if not cap.grab():
            break
        while ptr < len(order) and los[order[ptr]] <= n:
            active.append(order[ptr])
            ptr += 1
        if active and his[active[0]] < n:
            active = [i for i in active if his[i] >= n]
        if n % step or not active:
            continue
        ok, frame = cap.retrieve()
        if not ok or frame is None:
            continue
        th = thumb(frame).astype(np.int16)
        for i in active:
            it = items[i]
            if it['hits_n'] >= MAX_HITS:
                continue
            it['n_cmp'] += 1
            mae = float(np.abs(th - it['ref']).mean())
            if mae > MAE_OK:
                continue
            it['hits_n'] += 1
            segs = [s for s in split_lines(frame, SCAN_TOP, SCAN_BOT)
                    if s[1] - s[0] >= MIN_SEG_H and s[2] >= MIN_SEG_FILL]
            segs.sort(key=lambda s: -s[2])
            recs = []
            for y0, y1, fill in segs[:MAX_SEGS]:
                tx = tight_x(frame, y0, y1)
                if not tx:
                    continue
                ta = time.time()
                r = rec_pair(ocr, frame, y0, y1, tx, paths)
                t_ocr += time.time() - ta
                n_rec += len(paths)
                recs.append(dict(r, y0=y0, y1=y1, fill=fill, x0=tx[0], x1=tx[1],
                                 sim_old=round(max(sim(r.get(p, ''), it['old']) for p in paths), 3)))
            it['hits'].append({'fno': n, 't': round(n / fps, 2), 'mae': round(mae, 2), 'segs': recs})
    cap.release()
    el = time.time() - t0
    for it in items:
        it.pop('ref', None)
        it['best'] = max([s['sim_old'] for h in it['hits'] for s in h['segs']] or [0.0])
        it['offset'] = round(it['hits'][0]['t'] - it['sec'], 2) if it['hits'] else None
    out = {'ep': ep, 'title': title, 'fps': round(fps, 4), 'step': step, 'R': R,
           'paths': list(paths), 'n_entries': len(data), 'n_rec': n_rec,
           'n_located': sum(1 for it in items if it['hits']),
           'elapsed': round(el, 1), 'elapsed_ocr': round(t_ocr, 1), 'items': items}
    json.dump(out, open(os.path.join(OUT_DIR, f'q_online_{ep}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    offs = [it['offset'] for it in items if it['offset'] is not None]
    n_hit = sum(1 for it in items if it['best'] >= 0.95)
    n_mid = sum(1 for it in items if 0.6 <= it['best'] < 0.95)
    n_low = sum(1 for it in items if it['best'] < 0.6)
    print(f'{ep}: {len(data)} 条 / 定位 {out["n_located"]} / rec {n_rec} / '
          f'{el:.0f}s(OCR {t_ocr:.0f}s) | 一致 {n_hit} 部分 {n_mid} 不符 {n_low}', flush=True)
    if offs:
        print(f'   定位偏移: 最小 {min(offs):+.2f}s 最大 {max(offs):+.2f}s '
              f'中位 {sorted(offs)[len(offs) // 2]:+.2f}s', flush=True)
    return out


def main():
    args = sys.argv[1:]
    step, R, paths = 6, 6.0, ('bin', 'raw')
    for key, cast in (('--step', int), ('--R', float)):
        if key in args:
            j = args.index(key)
            v = cast(args[j + 1])
            del args[j:j + 2]
            if key == '--step':
                step = v
            else:
                R = v
    if '--paths' in args:
        j = args.index('--paths')
        paths = tuple(args[j + 1].split(','))
        del args[j:j + 2]
    eps = [a for a in args if not a.startswith('-')] or ['P01']
    ocr = build_engine()
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    print(f'q_online 就绪 step={step} R={R} paths={paths}', flush=True)
    for ep in eps:
        run_ep(ocr, ep, step, R, paths)


if __name__ == '__main__':
    main()
