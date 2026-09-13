# -*- coding: utf-8 -*-
"""q_reframe.py — 重新抽取"帧图与文本对不上"的条目的画面帧。

背景(实测): 现有帧图有两类错位来源, 会让条目显示的是**相邻台词**的画面 ——
  1) make_frames_full.py 用 cap.set(CAP_PROP_POS_MSEC) 定位, 实际落点与请求时刻有偏差;
  2) make_frames_map.py 有 ±3s 回退窗口: 7206 条里 1108 条用了非本秒的帧, 其中 225 条 |偏移|>=2s。
对这类条目, 网站"点台词看画面"看到的是另一句话。

做法: 对每条, 从它自己的时间戳 t 出发向两侧逐帧扩展 [t-1.6, t+1.6], 用字幕带签名去重
(签名相同则不重复识别), 找到**字幕读数与库文本一致(sim>=0.95)** 的帧, 按原帧图规格
(960x540 JPEG q80) 导出。找不到匹配帧的条目原样保留并报告。

用法: python q_reframe.py --src q_reframe_tg.json [--out Web/frames_fix] [--dry]
输出: <out>/<原帧名> + review/q_reframe_report.json
"""
import json
import os
import re
import sys
import time

import cv2
import numpy as np

from q_common import build_engine, sim
from q_subband import read_subs

B = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(B, 'Videos')
REVIEW = os.path.join(B, 'review')
FRAMES = os.path.join(B, 'Web', 'frames')
OUT_DEF = os.path.join(B, 'Web', 'frames_fix')
W, H = 960, 540
HALF = 1.6           # 向两侧各扩展的秒数
SIG_IOU = 0.92       # 相邻帧字幕带签名 IoU 高于此值 -> 视为同一句, 跳过识别
MATCH = 0.95


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def sig(frame):
    """字幕带纯白签名: 先按 >235 取掩膜再缩放(反过来会把细笔画平均掉)。"""
    h = frame.shape[0]
    c = frame[int(820 * h / 1080):]
    m = (c.min(axis=2) > 235).astype(np.float32)
    return cv2.resize(m, (192, 24), interpolation=cv2.INTER_AREA)


def sig_iou(a, b, t=0.2):
    A, Bb = a > t, b > t
    u = np.logical_or(A, Bb).sum()
    return float(np.logical_and(A, Bb).sum()) / u if u else 1.0


def save_frame(frame, fname, out_dir):
    h, w = frame.shape[:2]
    s = min(W / w, H / h)
    nw, nh = int(w * s), int(h * s)
    r = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = cv2.copyMakeBorder(r, (H - nh) // 2, H - nh - (H - nh) // 2,
                                (W - nw) // 2, W - nw - (W - nw) // 2,
                                cv2.BORDER_CONSTANT, value=(0, 0, 0))
    cv2.imwrite(os.path.join(out_dir, fname), canvas, [cv2.IMWRITE_JPEG_QUALITY, 80])


def run_ep(ocr, ep, items, out_dir, dry, step=1):
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # 展开每个条目的候选帧号: 从中心向两侧, 每 step 帧采一次(字幕持续 >=0.5s, step=2 不会漏)
    plan = {}
    for it in items:
        c = int(round(it['sec'] * fps))
        order = [c]
        for d in range(1, int(HALF * fps) + 1):
            if c - d >= 0:
                order.append(c - d)
            if c + d < total:
                order.append(c + d)
        it['order'] = [f for f in order if (f - c) % step == 0]
        it['cursor'] = 0
        for f in it['order']:
            plan.setdefault(f, []).append(it)
    idx = sorted(plan)
    n, i, t0 = 0, 0, time.time()
    n_ocr = 0
    while i < len(idx):
        if not cap.grab():
            break
        if n == idx[i]:
            ok, fr = cap.retrieve()
            if ok:
                s = sig(fr)
                for it in plan[n]:
                    it.setdefault('prev_sig', None)
                    if it['prev_sig'] is not None and sig_iou(s, it['prev_sig']) >= SIG_IOU:
                        it['prev_sig'] = s
                        it['cursor'] += 1
                        continue
                    it['prev_sig'] = s
                    txts = [v for y0, y1, x0, x1, tb, tr in read_subs(ocr, fr) for v in (tb, tr) if v]
                    n_ocr += 1
                    best = max(txts, key=lambda t: sim(t, it['old'])) if txts else ''
                    if best and sim(best, it['old']) >= MATCH:
                        it['hit_fno'] = n
                        it['hit_text'] = best
                        it['frame'] = fr.copy() if not dry else None
                    it['cursor'] += 1
            i += 1
        n += 1
    cap.release()

    rows = []
    for it in items:
        r = {'ep': ep, 'ts': it['ts'], 'old': it['old'], 'frame': it['frame_name'],
             'hit_fno': it.get('hit_fno'), 'hit_text': it.get('hit_text', ''),
             'dt': round(it['hit_fno'] / fps - it['sec'], 2) if it.get('hit_fno') is not None else None}
        if it.get('frame') is not None and not dry:
            save_frame(it['frame'], it['frame_name'], out_dir)
            r['saved'] = True
        rows.append(r)
    n_hit = sum(1 for r in rows if r['hit_fno'] is not None)
    print(f'  {ep}: {len(rows)} 条, 找到匹配帧 {n_hit}, OCR {n_ocr} 次 / {time.time() - t0:.0f}s',
          flush=True)
    return rows


def main():
    args = sys.argv[1:]
    src, out_dir, dry, step = 'q_reframe_tg.json', OUT_DEF, '--dry' in args, 1
    if '--src' in args:
        src = args[args.index('--src') + 1]
    if '--out' in args:
        out_dir = args[args.index('--out') + 1]
    if '--step' in args:
        step = int(args[args.index('--step') + 1])
    tag = ''
    if '--tag' in args:
        tag = args[args.index('--tag') + 1]
    eps_arg = [a for a in args if a.startswith('P') and a[1:].isdigit()]
    todo = json.load(open(os.path.join(REVIEW, src), encoding='utf-8'))
    by_ep = {}
    for r in todo:
        sec = parse_ts(r['ts'])
        if sec is not None:
            by_ep.setdefault(r['ep'], []).append(
                {'ts': r['ts'], 'sec': sec, 'old': r['old'], 'frame_name': r.get('frame')})
    os.makedirs(out_dir, exist_ok=True)
    print(f'q_reframe: {len(todo)} 条 / {len(by_ep)} 集 -> {out_dir}'
          f'{" (预演)" if dry else ""} step={step}', flush=True)
    ocr = build_engine()
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    rows = []
    todo_eps = eps_arg or sorted(by_ep)
    for ep in todo_eps:
        if ep in by_ep:
            rows.extend(run_ep(ocr, ep, by_ep[ep], out_dir, dry, step))
    out = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'dry': dry, 'n': len(rows),
           'n_hit': sum(1 for r in rows if r['hit_fno'] is not None), 'rows': rows}
    json.dump(out, open(os.path.join(REVIEW, f'q_reframe_report{tag}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"\n合计 {out['n']} 条, 找到匹配帧 {out['n_hit']} 条")
    print(f'输出: review/q_reframe_report{tag}.json')


if __name__ == '__main__':
    main()
