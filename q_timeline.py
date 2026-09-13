# -*- coding: utf-8 -*-
"""q_timeline.py — 全片字幕时间线重扫(文本质量提升的主数据源)。

设计依据(本轮实测):
  * 库时间戳与视频时间轴不同步(实测偏移 -3.2s ~ +1.1s, 且随区间变化), 所以"按库时间戳取帧"会
    大量读到邻句 —— q_rescan 在 P02 有 32% 条目同源失败;
  * 已存帧图与库文本一致(抽帧时 OCR 校验过), 但帧图只有 960x540, 分辨率不够修正细节;
  * 顺序 grab 全片仅需 ~450fps(78s/集), retrieve 一帧 12ms, rec 一次 46ms 与图尺寸无关。

于是改为: 每 0.25s 取一帧 -> 字幕带白像素签名 -> 仅当签名变化(且距上次识别 >=0.5s)才 OCR,
得到覆盖全片的字幕时间线; 同句字幕的多次识别天然构成投票。后续用 q_align.py 与库条目对齐。

用法: python q_timeline.py P01 [P02 ...] [--step 6] [--gap 12] [--th 0.02]
输出: review/q_timeline_<EP>.json
"""
import json
import os
import re
import sys
import time

import cv2
import numpy as np

from q_common import (SCAN_TOP, SCAN_BOT, build_engine, split_lines)
from q_rescan import rec_pair, tight_x, MIN_SEG_FILL, MIN_SEG_H, MAX_SEGS

B = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(B, 'Videos')
OUT_DIR = os.path.join(B, 'review')
BAND = (840, 1080)      # 字幕带(y 方向, 1080p): 比窄带 895~985 宽, 覆盖低位字幕行
SIG_SZ = (192, 24)
SIG_WHITE = 235         # 纯白阈值: 字幕是纯白, 提高阈值可压低画面亮部干扰
SIG_RATIO = 0.15        # 缩放后的白像素占比阈值
SIG_TH = 0.006          # 相邻采样帧签名差异超过此值 -> 认为字幕换句(实测换句时 0.008~0.05)
MIN_GAP = 12            # 距上次 OCR 至少这么多帧(0.5s), 防止画面运动反复触发


def signature(frame):
    """字幕带签名: 先按纯白阈值取掩膜, 再缩放成占比图并二值化。

    若先缩放后阈值, 细笔画会被 INTER_AREA 平均掉 —— 实测某段字幕签名白像素直接归零,
    导致整段字幕一次 OCR 都没触发(时间线漏掉 5 句)。
    """
    c = frame[BAND[0]:BAND[1]]
    m = (np.minimum(np.minimum(c[:, :, 0], c[:, :, 1]), c[:, :, 2]) > SIG_WHITE).astype(np.float32)
    s = cv2.resize(m, SIG_SZ, interpolation=cv2.INTER_AREA)
    return (s > SIG_RATIO).astype(np.uint8)


def scan_ep(ocr, ep, step=6, th=SIG_TH, gap=MIN_GAP, paths=('bin', 'raw')):
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    pts, prev_sig, last_ocr = [], None, -10 ** 9
    n = 0
    t0 = time.time()
    t_ocr = 0.0
    n_rec = 0
    while n < total:
        if not cap.grab():
            break
        if n % step == 0:
            ok, frame = cap.retrieve()
            if ok and frame is not None:
                sig = signature(frame)
                n_white = int(sig.sum())
                diff = 1.0 if prev_sig is None else float(
                    np.abs(sig.astype(np.int16) - prev_sig.astype(np.int16)).mean())
                prev_sig = sig
                pt = {'fno': n, 't': round(n / fps, 2), 'white': n_white, 'diff': round(diff, 4)}
                if n_white == 0:
                    pt['ocr'] = False
                elif diff > th and n - last_ocr >= gap:
                    last_ocr = n
                    pt['ocr'] = True
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
                    pt['segs'] = recs
                else:
                    pt['ocr'] = False
                pts.append(pt)
        n += 1
        if n % 12000 == 0:
            print(f'   {ep} {n}/{total} {time.time() - t0:.0f}s ocr帧 {sum(1 for p in pts if p.get("ocr"))}',
                  flush=True)
    cap.release()
    el = time.time() - t0
    out = {'ep': ep, 'fps': round(fps, 4), 'step': step, 'sig_th': th, 'min_gap': gap,
           'paths': list(paths), 'n_points': len(pts), 'n_ocr': sum(1 for p in pts if p.get('ocr')),
           'n_rec': n_rec, 'elapsed': round(el, 1), 'elapsed_ocr': round(t_ocr, 1), 'points': pts}
    json.dump(out, open(os.path.join(OUT_DIR, f'q_timeline_{ep}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'{ep}: 采样 {len(pts)} 点 / OCR {out["n_ocr"]} 次 / rec {n_rec} / {el:.0f}s'
          f'(OCR {t_ocr:.0f}s)', flush=True)
    return out


def main():
    args = sys.argv[1:]
    step, th, gap = 6, SIG_TH, MIN_GAP
    for key in ('--step', '--gap'):
        if key in args:
            j = args.index(key)
            v = int(args[j + 1])
            del args[j:j + 2]
            if key == '--step':
                step = v
            else:
                gap = v
    if '--th' in args:
        j = args.index('--th')
        th = float(args[j + 1])
        del args[j:j + 2]
    eps = [a for a in args if not a.startswith('-')] or ['P01']
    ocr = build_engine()
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    print(f'q_timeline 就绪 step={step} th={th} gap={gap}', flush=True)
    for ep in eps:
        scan_ep(ocr, ep, step, th, gap)


if __name__ == '__main__':
    main()
