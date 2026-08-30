# -*- coding: utf-8 -*-
"""scan3_vl.py — 阶段2（paddle_env_vv + vl_deps 环境）：VL 精判候选帧

读阶段1的 review/cand_index.json + review/cand_frames/ 候选帧，
用 PaddleOCR-VL 识别并对库文本做分行匹配（LCS>=0.5 或包含），
命中保存 best 帧到 web/frames/；未命中保持空缺（宁缺毋滥）。

用法: python scan3_vl.py [--test]
"""
import json
import os
import re
import sys

import cv2

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FRAMES_DIR = os.path.join(BASE, 'web', 'frames')
CAND_DIR = os.path.join(BASE, 'review', 'cand_frames')
INDEX = os.path.join(BASE, 'review', 'cand_index.json')
W, H = 960, 540
MATCH_MIN = 0.5

sys.path.insert(0, BASE)
import vl_recheck_new


def ts_str(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def lcs(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i][j - 1], dp[i - 1][j])
    return dp[m][n]


def ratio(a, b):
    return lcs(a, b) / min(len(a), len(b)) if a and b else 0


def match_lines(lib_lines, ocr_text):
    ocr_lines = [x for x in re.split(r'[\s]+', ocr_text.strip()) if len(x) >= 2] or [ocr_text.strip()]
    for lib in lib_lines:
        lib_c = lib.replace(' ', '')
        if not lib_c:
            continue
        for ocr in ocr_lines:
            ocr_c = ocr.replace(' ', '')
            if not ocr_c:
                continue
            if ratio(lib_c, ocr_c) >= MATCH_MIN or lib_c in ocr_c or ocr_c in lib_c:
                return True
    return False


def main():
    import numpy as np
    test = '--test' in sys.argv
    index = json.load(open(INDEX, encoding='utf-8'))
    if test:
        index = [r for r in index if r.get('ep') == 'P03' and r.get('ts') == '7m12s']
    print(f'待判条目 {len(index)}', flush=True)

    fixed, still = [], []
    for item in index:
        ep, ts = item['ep'], item['ts']
        text = item.get('text', '')
        lib_lines = text.split('\n')
        best = None
        for c in item.get('cands', []):
            fp = os.path.join(CAND_DIR, c['file'])
            frame = cv2.imread(fp)
            if frame is None:
                continue
            vtext = vl_recheck_new.vl_ocr_frame(frame)
            if not vtext or not match_lines(lib_lines, vtext):
                continue
            ocr_c = vtext.replace(' ', '')
            bl = max((ratio(l.replace(' ', ''), ocr_c) for l in lib_lines if l), default=0)
            if best is None or bl > best[0]:
                best = (bl, frame, c['ms'])
                if bl >= 0.99:
                    break
        if best is not None:
            name = f'{ep}_{ts_str(round(best[2] / 1000))}.jpg'
            cv2.imwrite(os.path.join(FRAMES_DIR, name),
                        cv2.resize(best[1], (W, H)), [cv2.IMWRITE_JPEG_QUALITY, 82])
            fixed.append({'ep': ep, 'ts': ts, 'text': text, 'frame': name,
                          'ratio': round(best[0], 3)})
            if test:
                print(f'[test] 命中 {ep} {ts} -> {name} ratio {best[0]:.2f} ({text[:18]})', flush=True)
        else:
            still.append({'ep': ep, 'ts': ts, 'text': text[:30]})
            if test:
                print(f'[test] 未命中 {ep} {ts} ({text[:18]}) 候选 {len(item.get("cands", []))}', flush=True)
        print(f'  {ep} {ts} 处理完（命中 {len(fixed)}）', flush=True)

    print(f'\n结果: 命中 {len(fixed)} | 仍未命中 {len(still)}', flush=True)
    with open(os.path.join(BASE, 'review', 'frames_scan3_v5_fix.json'), 'w', encoding='utf-8') as fh:
        json.dump({'fixed': fixed, 'still': still}, fh, ensure_ascii=False, indent=1)
    print('记录: review/frames_scan3_v5_fix.json')


if __name__ == '__main__':
    main()
