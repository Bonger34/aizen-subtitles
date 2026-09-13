# -*- coding: utf-8 -*-
"""q_locate.py — 文本质量提升主流程: 用已存帧图在视频中反查真实帧, 再对 1080p 原帧重识别。

为什么不能直接用库时间戳取帧(实测结论):
  * 已存帧图是历史抽帧脚本用 cap.set(CAP_PROP_POS_MSEC) 得到的, 该 API 会落到关键帧附近,
    实测真实位置比文件名时间戳偏 -3.2s ~ +0.9s, 且 seek 复现率只有 37%、单次 615ms;
  * 所以改为: 顺序解码全片生成缩略图指纹 -> 用帧图做模板匹配定位真实帧 -> 再顺序 grab 取该帧。
帧图本身与库文本一致(抽帧时用 OCR 校验过), 因此定位到的 1080p 原帧就是"该条目的原始画面",
它的分辨率是帧图的两倍, 配合自适应行切分与双路识别即可得到更准的文本。

用法: python q_locate.py P01 [P02 ...]  [--paths bin,raw] [--R 5]
输出: review/q_final_<EP>.json
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
FR = os.path.join(B, 'Web', 'frames')
OUT_DIR = os.path.join(B, 'review')
SZ = (64, 36)
MAE_OK = 3.0        # 模板匹配判定阈值(逐帧顺序扫描实测精确命中 0.2~1, 画面相似但不同帧 >6)
NEAR = (0.0, -0.2, 0.2)   # 定位帧附近再取两帧做同句投票


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def load_map():
    s = open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


def thumb(img):
    return cv2.cvtColor(cv2.resize(img, SZ, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)


def scan_fp(cap, total, ep):
    """顺序解码全片, 生成每帧的 64x36 灰度缩略图指纹。"""
    fp = np.zeros((total, SZ[1], SZ[0]), np.uint8)
    n = 0
    t0 = time.time()
    while n < total:
        ok, f = cap.read()
        if not ok:
            break
        fp[n] = thumb(f)
        n += 1
        if n % 6000 == 0:
            print(f'   {ep} 指纹 {n}/{total} {time.time() - t0:.0f}s', flush=True)
    return fp[:n]


def locate(fp, fps, sec, ref, R):
    lo = max(0, int((sec - R) * fps))
    hi = min(len(fp), int((sec + R) * fps) + 1)
    if hi <= lo:
        return None, 1e9
    d = np.abs(fp[lo:hi].astype(np.int16) - ref.astype(np.int16)).mean(axis=(1, 2))
    j = int(d.argmin())
    return lo + j, float(d[j])


def process_ep(ocr, ep, paths=('bin', 'raw'), R=5.0):
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]
    title = fn[:-5]
    data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
    MAP = load_map()
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]

    items = [{'ts': e.get('timestamp'), 'old': e.get('text'), 'frame': MAP.get(f'{title}|{e["timestamp"]}'),
              'fno': None, 'mae': None, 'offset': None, 'frames': {}, 'best': 0.0, 'paths': list(paths)}
             for e in data]

    # ---- 阶段 1: 指纹 + 定位
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    t0 = time.time()
    fp = scan_fp(cap, total, ep)
    cap.release()
    t_fp = time.time() - t0
    n_loc = n_fail = 0
    for it in items:
        sec = parse_ts(it['ts'])
        ref_img = cv2.imread(os.path.join(FR, it['frame'])) if it['frame'] else None
        if ref_img is None or sec is None:
            continue
        fno, mae = locate(fp, fps, sec, thumb(ref_img), R)
        it['mae'] = round(mae, 2)
        if fno is not None and mae <= MAE_OK:
            it['fno'] = fno
            it['offset'] = round(fno / fps - sec, 2)
            n_loc += 1
        else:
            n_fail += 1
    del fp

    # ---- 阶段 2: 顺序 grab 取定位帧及其前后 0.2s, 宽裁剪双路识别
    want = {}
    for i, it in enumerate(items):
        if it['fno'] is None:
            continue
        for d in NEAR:
            f2 = it['fno'] + int(round(d * fps))
            if f2 >= 0:
                want.setdefault(f2, []).append(i)
    cap = cv2.VideoCapture(vid)
    n, t_ocr, n_rec = 0, 0.0, 0
    for fno in sorted(want):
        while n < fno:
            cap.grab()
            n += 1
        ok, frame = cap.read()
        n += 1
        if not ok or frame is None:
            continue
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
            recs.append(dict(r, y0=y0, y1=y1, fill=fill, x0=tx[0], x1=tx[1]))
        for i in want[fno]:
            old = items[i]['old']
            recs_i = [dict(r, sim_old=round(max(sim(r.get(p, ''), old) for p in paths), 3))
                      for r in recs]
            items[i]['frames'][str(fno)] = {'fno': fno, 'segs': recs_i}
            items[i]['best'] = max(items[i]['best'],
                                   max([r['sim_old'] for r in recs_i] or [0.0]))
    cap.release()

    el = time.time() - t0
    out = {'ep': ep, 'title': title, 'fps': round(fps, 4), 'paths': list(paths),
           'n_entries': len(data), 'n_locate': n_loc, 'n_locate_fail': n_fail,
           'n_rec': n_rec, 'elapsed': round(el, 1), 't_fp': round(t_fp, 1),
           'elapsed_ocr': round(t_ocr, 1), 'items': items}
    json.dump(out, open(os.path.join(OUT_DIR, f'q_final_{ep}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    n_hit = sum(1 for it in items if it['best'] >= 0.95)
    n_mid = sum(1 for it in items if 0.6 <= it['best'] < 0.95)
    n_low = sum(1 for it in items if it['best'] < 0.6)
    print(f'{ep}: {len(data)} 条 / 定位 {n_loc}(失败 {n_fail}) / rec {n_rec} / '
          f'{el:.0f}s(指纹 {t_fp:.0f}s OCR {t_ocr:.0f}s) | 一致 {n_hit} 部分 {n_mid} 不符 {n_low}',
          flush=True)
    return out


def main():
    args = sys.argv[1:]
    paths, R = ('bin', 'raw'), 5.0
    if '--paths' in args:
        j = args.index('--paths')
        paths = tuple(args[j + 1].split(','))
        del args[j:j + 2]
    if '--R' in args:
        j = args.index('--R')
        R = float(args[j + 1])
        del args[j:j + 2]
    eps = [a for a in args if not a.startswith('-')] or ['P01']
    ocr = build_engine()
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    print(f'q_locate 就绪 paths={paths} R={R}', flush=True)
    for ep in eps:
        process_ep(ocr, ep, paths, R)


if __name__ == '__main__':
    main()
