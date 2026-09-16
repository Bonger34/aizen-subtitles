# -*- coding: utf-8 -*-
"""q_edgecheck.py — 复核"边缘噪声/减字"类修正: 在 t±3s 内逐点读原片, 看画面支持旧文本还是新文本。

这一类修正当初的理由是"画面无某字 / 首字噪声 / 尾部噪声字"—— 判定依据是 960×540 的帧图
或错位的回退帧, 正是本轮实测最不可靠的两条路。已在 P02 9m50s、P04 3m39s 上确证改错。
本脚本对全库同类修正做一次统一复核: 哪个候选文本在窗口内被逐点读数支持得更好。

用法: python q_edgecheck.py
输出: review/q_edgecheck.json
"""
import json
import os
import re
import sys
import time

import cv2

import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import build_engine, norm, to_simp
from q_subband import read_subs

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(B, 'Videos')
REVIEW = os.path.join(B, 'review')
HALF, STEP = 3.0, 0.3


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def sim(a, b):
    a, b = norm(to_simp(a)), norm(to_simp(b))
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return 1.0 - prev[n] / min(m, n)


def main():
    man = json.load(open(os.path.join(REVIEW, 'q_manual_verdicts.json'), encoding='utf-8'))
    items = []
    for x in man.get('frame_apply', []):
        w = x.get('why', '')
        a, b = norm(x.get('old')), norm(x.get('new'))
        if any(k in w for k in ('噪声', '首字', '尾部', '多余', '多的')) or len(b) < len(a):
            items.append(x)
    print(f'待复核(边缘噪声/减字类) {len(items)} 条')

    by_ep = {}
    for x in items:
        s = parse_ts(x['ts'])
        if s is not None:
            by_ep.setdefault(x['ep'], []).append((s, x))
    ocr = build_engine()
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    ocr.text_rec(TextRecInput(img=__import__('numpy').zeros((64, 512, 3), __import__('numpy').uint8)))

    out = []
    for ep in sorted(by_ep):
        vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
               if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
        cap = cv2.VideoCapture(vid)
        fps = cap.get(cv2.CAP_PROP_FPS)
        want = {}
        for s, x in by_ep[ep]:
            for k in range(-int(HALF / STEP), int(HALF / STEP) + 1):
                want.setdefault(max(0, int(round((s + k * STEP) * fps))), []).append(x)
        idx = sorted(want)
        got = {}
        n = i = 0
        t0 = time.time()
        while i < len(idx):
            if not cap.grab():
                break
            if n == idx[i]:
                ok, fr = cap.retrieve()
                if ok:
                    txts = [v for y0, y1, x0, x1, tb, tr in read_subs(ocr, fr) for v in (tb, tr) if v]
                    for x in want[n]:
                        got.setdefault((x['ep'], x['ts']), []).extend(txts)
                i += 1
            n += 1
        cap.release()
        for s, x in by_ep[ep]:
            u = sorted(set(got.get((ep, x['ts']), [])))
            so = max((sim(t, x['old']) for t in u), default=0.0)
            sn = max((sim(t, x['new']) for t in u), default=0.0)
            verdict = '支持旧文本(该改回)' if so >= 0.95 and so > sn else (
                '支持新文本(修正正确)' if sn >= 0.95 and sn >= so else '无定论')
            out.append({'ep': ep, 'ts': x['ts'], 'old': x['old'], 'new': x['new'],
                        'why': x.get('why', ''), 'sim_old': round(so, 3), 'sim_new': round(sn, 3),
                        'verdict': verdict, 'readings': u[:4]})
        print(f'  {ep}: {len(by_ep[ep])} 条 / {time.time() - t0:.0f}s', flush=True)

    import collections
    c = collections.Counter(r['verdict'] for r in out)
    print('\n复核结果:', dict(c))
    for r in out:
        if r['verdict'] != '支持新文本(修正正确)':
            print(f"  [{r['verdict']}] {r['ep']} {r['ts']:>7s} [{r['old']}] -> [{r['new']}]  "
                  f"旧{r['sim_old']:.2f}/新{r['sim_new']:.2f}")
            print(f"        理由={r['why']}  窗口读数={r['readings']}")
    json.dump(out, open(os.path.join(REVIEW, 'q_edgecheck.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n输出: review/q_edgecheck.json')


if __name__ == '__main__':
    main()
