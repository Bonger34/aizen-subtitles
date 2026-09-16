# -*- coding: utf-8 -*-
"""q_locate2.py — 用「字幕带模板匹配」在 1080p 视频里反查帧图的真实帧, 再对原帧重识别。

为什么这条路之前没走通:
  1) q_locate 用 64x36 **全帧**指纹做匹配 —— 字幕只占极小面积, "画面相似但字幕不同"的帧会被
     认成命中(MAE 2.6~6.8)。改成只比**字幕带**(近白掩膜 + 归一化 + 白像素 IoU)后, 实测
     同一帧的 IoU 达 0.82~0.91, 而不同句字幕 IoU < 0.2。
  2) 扫描循环条件写成 any(窗口覆盖当前帧) —— 窗口之间有间隙, 一进间隙就退出, 实测 3 个任务
     只处理了 1 个。改为按最大上界循环。
  3) 定位到帧后仍读不出: 1080p 画面里人物的白衬衫与字幕都超过行阈值(峰值的 12%), 被连成
     235px 高的一整段, OCR 读不出。加 row_th_ratio=0.6 后只保留白像素密集的字幕行。

用法: python q_locate2.py [--src q_targets.json] [--half 5] [--row-th 0.6] [P01 ...]
输出: review/q_locate2_<EP>.json
"""
import json
import os
import re
import sys
import time
from collections import Counter

import cv2
import numpy as np

import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import SCAN_TOP, SCAN_BOT, build_engine, diff_rel, sim, split_lines
from q_rescan import rec_pair, tight_x, MIN_SEG_FILL, MIN_SEG_H, MAX_SEGS
from q_subband import read_subs

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(B, 'Videos')
FR = os.path.join(B, 'docs', 'frames')
CLEAN = os.path.join(B, 'subtitle_clean')
REVIEW = os.path.join(B, 'review')
BAND_TOP, BAND_BOT = 820, 1080     # 缓存与匹配用的字幕带(1080p 坐标)
SZ = (480, 60)
THR = 225
MAX_DENSITY, WHITE_MIN = 0.60, 230


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def band(img, sz=SZ, thr=THR):
    h = img.shape[0]
    y0 = int(BAND_TOP * h / 1080)
    c = img[y0:h]
    m = (np.minimum(np.minimum(c[:, :, 0], c[:, :, 1]), c[:, :, 2]) > thr).astype(np.float32)
    return cv2.resize(m, sz, interpolation=cv2.INTER_AREA)


def iou(a, b, t=0.25):
    A, B = a > t, b > t
    u = np.logical_or(A, B).sum()
    return float(np.logical_and(A, B).sum()) / u if u else 0.0


def load_map():
    s = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


def ocr_band(ocr, cached, old, row_th, paths=('bin', 'raw')):
    """对缓存的字幕带裁剪(cached 从 y=BAND_TOP 起)识别, 返回 (最佳sim, 文本, 行带, 方法)。

    主路: q_subband.read_subs —— 用"白像素∩邻域暗像素"定位字幕行并剔除大块白(衣物)。
    实测这一路解决了白掩膜剖面在大面积白衣物画面上失效的问题(P01 537.81s 「甚至还有点」)。
    备路: 旧的白掩膜行剖面 split_lines —— 只主路一无所获时才跑, 用于没有黑描边的字幕。
    """
    t, b = SCAN_TOP - BAND_TOP, SCAN_BOT - BAND_TOP
    # 初值必须低于任何可能的 sim: 旧文本只是少读几个字时(如 赢了 vs 我们赢了) sim 恰为 0.0,
    # 若初值取 0.0, 严格的 > 比较会把这条真实读数整个丢掉, 表现为"定位到了却读不出"。
    best = (-9.0, '', None, '')
    for y0, y1, x0, x1, tb, tr in read_subs(ocr, cached, t, b):
        for v in (tb, tr):
            if v:
                sc = sim(v, old)
                if sc > best[0]:
                    best = (sc, v, (y0 + BAND_TOP, y1 + BAND_TOP), 'subband')
    if best[1]:
        return best
    segs = [s for s in split_lines(cached, t, b, max_density=MAX_DENSITY, white_min=WHITE_MIN,
                                   row_th_ratio=row_th)
            if s[1] - s[0] >= MIN_SEG_H and s[2] >= MIN_SEG_FILL]
    segs.sort(key=lambda s: -s[2])
    for y0, y1, fill in segs[:MAX_SEGS]:
        tx = tight_x(cached, y0, y1)
        if not tx:
            continue
        rr = rec_pair(ocr, cached, y0, y1, tx, paths)
        for p in paths:
            v = rr.get(p) or ''
            if v:
                sc = sim(v, old)
                if sc > best[0]:
                    best = (sc, v, (y0 + BAND_TOP, y1 + BAND_TOP), 'split')
    return best


def run_ep(ocr, ep, targets, mapv, half=5.0, row_th=0.6, tag=''):
    title = next(t for t in mapv if t.startswith(f'[{ep}]')).split('|')[0]
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    tasks = []
    for r in targets:
        sec = parse_ts(r['ts'])
        f = mapv.get(f'{title}|{r["ts"]}')
        p = os.path.join(FR, f) if f else None
        img = cv2.imread(p) if p and os.path.exists(p) else None
        if img is None or sec is None:
            continue
        tasks.append({'ts': r['ts'], 'old': r['old'], 'sec': sec, 'ref': band(img),
                      'lo': max(0, int((sec - half) * fps)),
                      'hi': min(total - 1, int((sec + half) * fps))})
    if not tasks:
        cap.release()
        return []
    print(f'  {ep}: {len(tasks)} 条, 窗口 {sum(t["hi"] - t["lo"] for t in tasks) / fps:.0f}s',
          flush=True)

    n, t0 = 0, time.time()
    lo_all, hi_all = min(t['lo'] for t in tasks), max(t['hi'] for t in tasks)
    while n < lo_all:
        cap.grab()
        n += 1
    n_hit = 0
    while n <= hi_all:
        if not cap.grab():
            break
        act = [t for t in tasks if t['lo'] <= n <= t['hi']]
        if act:
            ok, frame = cap.retrieve()
            if ok:
                b = band(frame)
                for t in act:
                    v = iou(b, t['ref'])
                    if v > t.get('best_iou', -1):
                        t['best_iou'] = v
                        t['best_fno'] = n
                        # 缓存该帧的字幕带(约 1.5MB/条), 省去第二遍顺序读
                        t['cached'] = frame[BAND_TOP:BAND_BOT].copy()
                n_hit += 1
        n += 1
    cap.release()

    rows = []
    for t in tasks:
        t.pop('ref', None)
        cached = t.pop('cached', None)
        fno = t.get('best_fno')
        rec = {'ep': ep, 'ts': t['ts'], 'old': t['old'], 'fno': fno,
               'offset': round(fno / fps - t['sec'], 2) if fno is not None else None,
               'iou': round(t.get('best_iou', 0.0), 3), 'sim': 0.0, 'text': '',
               'seg': None, 'how': '', 'rel': ''}
        if cached is not None:
            sc, txt, seg, how = ocr_band(ocr, cached, t['old'], row_th)
            rec.update(sim=round(sc, 3), text=txt, seg=seg, how=how,
                       rel=diff_rel(t['old'], txt))
        rows.append(rec)
    el = time.time() - t0
    json.dump(rows, open(os.path.join(REVIEW, f'q_locate2{tag}_{ep}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    n_ok = sum(1 for r in rows if r['sim'] >= 0.9)
    n_mid = sum(1 for r in rows if 0.55 <= r['sim'] < 0.9)
    n_none = sum(1 for r in rows if r['fno'] is not None and not r['text'])
    rels = Counter(r['rel'] for r in rows if r['rel'])
    print(f'  {ep}: 定位 {sum(1 for r in rows if r["fno"] is not None)}/{len(rows)} / '
          f'证实 {n_ok} / 候选 {n_mid} / 无字幕或读不出 {n_none} / '
          f'{dict(rels)} / {el:.0f}s', flush=True)
    return rows


def main():
    args = sys.argv[1:]
    src, half, row_th, tag, eps_arg = 'q_targets.json', 5.0, 0.6, '', []
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--src':
            src = args[i + 1]; i += 2
        elif a == '--half':
            half = float(args[i + 1]); i += 2
        elif a == '--row-th':
            row_th = float(args[i + 1]); i += 2
        elif a == '--tag':
            tag = args[i + 1]; i += 2
        else:
            eps_arg.append(a); i += 1
    todo = json.load(open(os.path.join(REVIEW, src), encoding='utf-8'))
    by_ep = {}
    for r in todo:
        by_ep.setdefault(r['ep'], []).append(r)
    eps = eps_arg or sorted(by_ep)
    print(f'q_locate2{tag}: {len(todo)} 条 / {len(eps)} 集 (src={src}, half={half}, '
          f'row_th={row_th})', flush=True)

    mapv = load_map()
    ocr = build_engine()
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    all_rows = []
    for ep in eps:
        if ep in by_ep:
            all_rows.extend(run_ep(ocr, ep, by_ep[ep], mapv, half, row_th, tag))
    json.dump(all_rows, open(os.path.join(REVIEW, f'q_locate2{tag}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    n_ok = sum(1 for r in all_rows if r['sim'] >= 0.9)
    n_mid = sum(1 for r in all_rows if 0.55 <= r['sim'] < 0.9)
    n_loc = sum(1 for r in all_rows if r['fno'] is not None)
    n_sub = sum(1 for r in all_rows if r.get('how') == 'subband')
    n_none = sum(1 for r in all_rows if r['fno'] is not None and not r['text'])
    print(f'\n合计 {len(all_rows)} 条: 定位成功 {n_loc} / 证实旧文本 {n_ok} / 候选 {n_mid} / '
          f'无字幕或读不出 {n_none} (其中白边掩膜路命中 {n_sub})')
    print(f'输出: review/q_locate2{tag}.json + review/q_locate2{tag}_<EP>.json')


if __name__ == '__main__':
    main()
