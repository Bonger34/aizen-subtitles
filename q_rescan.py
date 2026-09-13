# -*- coding: utf-8 -*-
"""q_rescan.py — 全库文本质量提升: 原帧重扫(自适应行切分 + 双路识别 + 多帧投票)。

背景与事实依据:
  * 库文本由固定窄带 (100,895,1820,985) 生成, 实测 28.6% 帧的主文字行下缘伸出 985, 被切字;
  * 片头 OP(日文歌词)/片尾 ED(演职员表) 段用同一窄带会把两类文字混读成乱码;
  * 已按文字行切好的单行带不需要再做检测(det), 直接跑识别(rec)快 14 倍(实测 0.636s -> 0.045s/次)。

做法: 顺序读原片(禁用 seek) -> 每条目取 3 帧 -> 每帧按白像素行剖面切段 -> 段内紧裁 x
      -> 二值化/原始 两路 rec -> 结果交 q_judge.py 判定。

用法: python q_rescan.py [--limit N] P01 [P02 ...]
输出: review/q_rescan_<EP>.json
"""
import json
import os
import re
import sys
import time

import cv2
import numpy as np

from q_common import (SCAN_TOP, SCAN_BOT, X0, X1, PAD_Y, build_engine, crop_norm,
                      gray_white, sim, split_lines)

B = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle_clean')
OUT_DIR = os.path.join(B, 'review')
OFFSETS = (0.05, 0.3, 0.55, 0.8)  # 覆盖 [t, t+1): 时间戳只有秒级精度, 字幕实际起点在区间内任意处
MIN_SEG_H = 18              # 段高下限: 低于此视为画面细线/噪声
MIN_SEG_FILL = 600          # 段内白像素总数下限
MAX_SEGS = 3                # 每帧最多识别的段数(按白像素密度降序)
X_PAD = 16
HIT_SIM = 0.95              # 某帧已与该条目旧文本高度一致 -> 后续帧不再为该条目重复识别


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def tight_x(img, y0, y1, pad=X_PAD):
    """按列投影裁到文字实际水平范围 —— 直接减少 rec 输入宽度(耗时正比于宽度)。"""
    sx, sy = img.shape[1] / 1920.0, img.shape[0] / 1080.0
    sub = gray_white(img[max(0, int((y0 - 2) * sy)):int((y1 + 2) * sy),
                         int(X0 * sx):int(X1 * sx)])
    nz = np.where(sub.sum(axis=0) > 0)[0]
    if len(nz) == 0:
        return None
    return (max(X0, int(X0 + (nz[0] - pad) / sx)),
            min(X1, int(X0 + (nz[-1] + pad) / sx)))


def rec_pair(ocr, frame, y0, y1, tx, paths=('bin', 'raw')):
    """同段多路识别: bin=二值化(白底黑字, 与原管线一致) / raw=原始彩色 —— 互为独立投票。"""
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    out = {}
    for tag in ('bin', 'raw'):
        if tag not in paths:
            continue
        if tag == 'bin':
            img = crop_norm(frame, (tx[0], y0 - PAD_Y, tx[1], y1 + PAD_Y), upscale=1.0)
        else:
            sx, sy = frame.shape[1] / 1920.0, frame.shape[0] / 1080.0
            img = frame[max(0, int((y0 - PAD_Y) * sy)):int((y1 + PAD_Y) * sy),
                        int(tx[0] * sx):int(tx[1] * sx)]
        if img is None or img.size == 0:
            out[tag], out[tag + '_score'] = '', 0.0
            continue
        try:
            r = ocr.text_rec(TextRecInput(img=img))
            out[tag] = r.txts[0] if r.txts else ''
            out[tag + '_score'] = round(float(r.scores[0]), 4) if r.scores else 0.0
        except Exception:
            out[tag], out[tag + '_score'] = '', 0.0
    return out


def scan_ep(ocr, ep, limit=0, n_frames=3, paths=('bin', 'raw')):
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]
    data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
    if limit:
        data = data[:limit]
    offs = OFFSETS[:n_frames]
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    want = {}
    for i, e in enumerate(data):
        sec = parse_ts(e.get('timestamp'))
        if sec is None:
            continue
        for k, off in enumerate(offs):
            fno = min(total - 1, max(0, int(round((sec + off) * fps))))
            want.setdefault(fno, []).append((i, k))

    items = [{'ts': e.get('timestamp'), 'old': e.get('text'), 'frames': [None] * len(offs),
              'done': False, 'best': 0.0}
             for e in data]
    n, t_ocr, n_rec, n_skip = 0, 0.0, 0, 0
    t0 = time.time()
    for idx, fno in enumerate(sorted(want)):
        if idx and idx % 500 == 0:
            print(f'   {ep} {idx}/{len(want)} 帧, {time.time() - t0:.0f}s', flush=True)
        pending = [(i, k) for i, k in want[fno] if not items[i]['done']]
        while n < fno:
            cap.grab()
            n += 1
        if not pending:          # 该帧关联的条目都已有高相似帧 -> 丢弃该帧, 不解码不识别
            cap.grab()
            n += 1
            n_skip += 1
            continue
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
        payload = {'fno': fno, 'segs': recs}
        for i, k in pending:
            items[i]['frames'][k] = payload
            old = data[i].get('text', '')
            s = max([sim(r.get(p, ''), old) for r in recs for p in paths] or [0.0])
            if s > items[i]['best']:
                items[i]['best'] = round(s, 3)
            if s >= HIT_SIM:
                items[i]['done'] = True
    cap.release()
    el = time.time() - t0
    out = {'ep': ep, 'title': fn[:-5], 'fps': round(fps, 4), 'offsets': list(offs),
           'paths': list(paths), 'n_entries': len(data), 'n_targets': len(want),
           'n_skip': n_skip, 'n_rec': n_rec, 'elapsed': round(el, 1),
           'elapsed_ocr': round(t_ocr, 1), 'items': items}
    json.dump(out, open(os.path.join(OUT_DIR, f'q_rescan_{ep}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    n_hit = sum(1 for it in items if it['best'] >= HIT_SIM)
    n_mid = sum(1 for it in items if 0.6 <= it['best'] < HIT_SIM)
    n_low = sum(1 for it in items if it['best'] < 0.6)
    print(f'{ep}: {len(data)} 条 / 目标帧 {len(want)}(跳 {n_skip}) / rec {n_rec} 次 / '
          f'用时 {el:.1f}s(OCR {t_ocr:.1f}s, {t_ocr / max(1, n_rec) * 1000:.0f}ms/次)', flush=True)
    print(f'   旧文本被证实: {n_hit} | 部分相似(0.6~0.95): {n_mid} | 帧内未找到(<0.6): {n_low}',
          flush=True)
    return out


def main():
    args = sys.argv[1:]
    limit = 0
    n_frames = len(OFFSETS)
    paths = ('bin', 'raw')
    if '--limit' in args:
        j = args.index('--limit')
        limit = int(args[j + 1])
        del args[j:j + 2]
    if '--frames' in args:
        j = args.index('--frames')
        n_frames = int(args[j + 1])
        del args[j:j + 2]
    if '--paths' in args:
        j = args.index('--paths')
        paths = tuple(args[j + 1].split(','))
        del args[j:j + 2]
    eps = [a for a in args if not a.startswith('-')] or ['P01']
    ocr = build_engine()
    # 预热: 首次 rec 有 ~20s 的 CUDA 初始化, 不计入单集耗时
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    import numpy as np
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    print(f'RapidOCR rec-only 就绪(rec_img_shape={ocr.text_rec.rec_image_shape}), '
          f'frames={n_frames} paths={paths} limit={limit}', flush=True)
    for ep in eps:
        scan_ep(ocr, ep, limit, n_frames, paths)


if __name__ == '__main__':
    main()
