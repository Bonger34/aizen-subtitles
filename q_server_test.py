# -*- coding: utf-8 -*-
"""q_server_test.py — 试更强的识别模型(PP-OCRv6 SERVER)能否救回帧图读不出的条目。

帧图只有 960x540, MEDIUM 模型在亮背景/小字上大量漏读; SERVER 模型参数量更大, 或许能读出。
用法: python q_server_test.py [条数=20]
输出: review/q_server_test.json + 控制台对照
"""
import json
import os
import sys
import time

import cv2
import numpy as np

from q_common import (SCAN_TOP, SCAN_BOT, build_engine, sim, split_lines)
from rapidocr.utils.parse_parameters import ModelType

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
FR = os.path.join(B, 'docs', 'frames')
MAX_DENSITY, WHITE_MIN = 0.60, 230


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    from q_final import edit_kind  # noqa: E402
    items = [r for r in json.load(open(os.path.join(REVIEW, 'q_final.json'), encoding='utf-8'))
             if r['band'] == 'unreadable'][:n]
    print(f'测试 {len(items)} 条 (SERVER 模型)', flush=True)
    ocr = build_engine(rec_model_type=ModelType.SERVER)
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    paths = ('bin', 'raw')
    out = []
    t0 = time.time()
    from q_rescan import rec_pair, tight_x
    for r in items:
        img = cv2.imread(os.path.join(FR, r['frame'])) if r.get('frame') else None
        rec = dict(r)
        rec['server_text'] = ''
        rec['server_sim'] = 0.0
        if img is not None:
            segs = [s for s in split_lines(img, SCAN_TOP, SCAN_BOT,
                                           max_density=MAX_DENSITY, white_min=WHITE_MIN)
                    if s[1] - s[0] >= 18 and s[2] >= 600]
            segs.sort(key=lambda s: -s[2])
            cands = []
            for y0, y1, fill in segs[:3]:
                tx = tight_x(img, y0, y1)
                if not tx:
                    continue
                rr = rec_pair(ocr, img, y0, y1, tx, paths)
                for p in paths:
                    v = rr.get(p) or ''
                    if v:
                        cands.append((sim(v, r['old']), v))
            if cands:
                rec['server_sim'], rec['server_text'] = max(cands)
                rec['server_sim'] = round(rec['server_sim'], 3)
        rec['kind2'], rec['desc2'] = edit_kind(r['old'], rec['server_text'])
        out.append(rec)
    el = time.time() - t0
    n_ok = sum(1 for r in out if r['server_sim'] >= 0.9)
    n_mid = sum(1 for r in out if 0.55 <= r['server_sim'] < 0.9)
    print(f'耗时 {el:.0f}s ({el / max(1, len(out)):.1f}s/条)')
    print(f'SERVER 结果: 证实 {n_ok} / 候选 {n_mid} / 仍读不出 {len(out) - n_ok - n_mid}')
    print(f'(对照: MEDIUM 对同一批全部读不出)')
    for r in out:
        if r['server_sim'] >= 0.55:
            print(f"  {r['ep']} {r['ts']:>7s} sim={r['server_sim']:.2f} [{r['kind2']}] {r['desc2']}")
            print(f"      旧[{r['old']}]")
            print(f"      S[{r['server_text']}]")
    json.dump(out, open(os.path.join(REVIEW, 'q_server_test.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
