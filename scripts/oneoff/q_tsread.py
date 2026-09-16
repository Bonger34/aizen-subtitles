# -*- coding: utf-8 -*-
"""q_tsread.py — **按库时间戳直接读原片**: 完全不依赖帧图, 是文本对错的最终判据。

为什么需要它:
  q_locate2 是"拿帧图去视频里找同一帧再读", 但帧图本身可能是错的 —— 实测
  make_frames_full.py 用 cap.set(CAP_PROP_POS_MSEC) 定位, 实际落点比请求时刻晚约 0.8s;
  make_frames_map.py 又有 ±3s 的回退窗口。两者叠加会让若干条目的帧图显示的是**相邻台词**
  (实测 7206 条里 1108 条用了回退帧, 其中 225 条 |偏移|>=2s)。对这类条目, q_locate2 读到的
  是邻居的台词, 据此改文本会把对的文本改错。
  本脚本用顺序 grab()(帧精确, 不受 seek 漂移影响) 在库时间戳 t、t+0.4、t+0.8 三点各读一次,
  三点读数互相独立, 直接反映"该时刻画面上真正的字幕"。

用法: python q_tsread.py --src q_targets.json [--tag ts] [--eps P01 P02]
输出: review/q_tsread<tag>_<EP>.json + review/q_tsread<tag>.json
"""
import json
import os
import re
import sys
import time

import cv2

import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import build_engine
from q_subband import read_subs

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(B, 'Videos')
REVIEW = os.path.join(B, 'review')
OFFS = (-0.8, -0.4, 0.0, 0.4, 0.8)   # 秒; 库时间戳只有秒级精度, 且实测显示时刻与库时间戳
                                     # 有 ±1s 级别的错位, 取五点覆盖该秒前后各一档
# 宽松档: 实测残留条目的主因是"识别读漏"(库[真不愧是爱染先生]只读到[真不愧先生]),
# 偏暗/偏小的字在默认白阈值 200 下会被丢掉, 故严格档读不出时用这组参数再读一次。
RELAX = {'w_thr': 180, 'max_cc_w': 400, 'max_cc_h': 160, 'min_cc_a': 60, 'ratio': 0.25}


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def read_times(ocr, ep, times, relax=True):
    """顺序读该集一次, 返回 {t: [文本, ...]}。"""
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    want = {}
    for t in times:
        for o in OFFS:
            # 必须夹到 >=0: 首条 0m00s 减 0.8s 会得到负帧号, 会让下面的 while 永远匹配不上,
            # 结果整集一路 grab 到底、所有条目都读成空(实测 P01/P02 276+283 条全空)。
            want.setdefault(max(0, int(round((t + o) * fps))), []).append((t, o))
    idx = sorted(want)
    out = {t: [] for t in times}
    n, i, n_relax = 0, 0, 0
    while i < len(idx):
        if not cap.grab():
            break
        if n == idx[i]:
            ok, fr = cap.retrieve()
            if ok:
                txts = [v for y0, y1, x0, x1, tb, tr in read_subs(ocr, fr) for v in (tb, tr) if v]
                if relax:
                    # 只在严格档没读到"够长"的句子时才跑宽松档, 避免全量双倍开销
                    good = max((len(t) for t in txts), default=0) >= 4
                    if not good:
                        n_relax += 1
                        txts += [v for y0, y1, x0, x1, tb, tr in read_subs(ocr, fr, **RELAX)
                                 for v in (tb, tr) if v]
                for t, o in want[n]:
                    out[t].append({'off': o, 'texts': txts})
            i += 1
        n += 1
    cap.release()
    return out, n_relax


def main():
    args = sys.argv[1:]
    src, tag, eps_arg, relax = 'q_targets.json', '', [], True
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--src':
            src = args[i + 1]; i += 2
        elif a == '--tag':
            tag = args[i + 1]; i += 2
        elif a == '--no-relax':
            relax = False; i += 1
        else:
            eps_arg.append(a); i += 1
    todo = json.load(open(os.path.join(REVIEW, src), encoding='utf-8'))
    by_ep = {}
    for r in todo:
        sec = parse_ts(r['ts'])
        if sec is not None:
            by_ep.setdefault(r['ep'], {})[sec] = r
    eps = eps_arg or sorted(by_ep)
    print(f'q_tsread{tag}: {len(todo)} 条 / {len(eps)} 集 (src={src}, 宽松档={relax})', flush=True)

    ocr = build_engine()
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    ocr.text_rec(TextRecInput(img=__import__('numpy').zeros((64, 512, 3), __import__('numpy').uint8)))

    rows = []
    for ep in eps:
        if ep not in by_ep:
            continue
        t0 = time.time()
        res, n_relax = read_times(ocr, ep, sorted(by_ep[ep]), relax)
        n_sub = 0
        for sec, r in sorted(by_ep[ep].items()):
            reads = res.get(sec, [])
            texts = [t for rd in reads for t in rd['texts']]
            # 读数里出现次数最多者作代表
            best, bestn = '', 0
            for t in texts:
                c = texts.count(t)
                if c > bestn or (c == bestn and len(t) > len(best)):
                    best, bestn = t, c
            if best:
                n_sub += 1
            rows.append({'ep': ep, 'ts': r['ts'], 'old': r['old'], 'why': r.get('why', ''),
                         'reads': reads, 'text': best, 'n': bestn,
                         'all': sorted(set(texts))})
        json.dump(rows, open(os.path.join(REVIEW, f'q_tsread{tag}_{ep}.json'), 'w',
                             encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'  {ep}: {len(by_ep[ep])} 条, 有字幕 {n_sub}, 宽松档补读 {n_relax} 帧 / '
              f'{time.time() - t0:.0f}s', flush=True)
    json.dump(rows, open(os.path.join(REVIEW, f'q_tsread{tag}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'输出: review/q_tsread{tag}.json')


if __name__ == '__main__':
    main()
