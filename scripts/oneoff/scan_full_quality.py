# -*- coding: utf-8 -*-
"""scan_full_quality.py — 全库文本质量复核 v2（PP-OCRv5/v6 server · GPU）

v1 教训：全帧 OCR 会混入右上水印(bilibili正版)与顶部信息字；繁简差异(凑/湊)降低匹配。
v2 修正：
  1. OCR 输入 = 底部字幕带裁剪（SUBTITLE_AREA），避开画面其他文字；空结果补反色二值化通道
  2. opencc t2s 繁简归一 + 仅汉字串比对
  3. 应用条件：ratio(lib,ocr)>=0.90 且 汉字数差<=2 → 采用 denoised 文本；
     0.40~0.90 → 候选清单；<0.40 或未读到 → 跳过
用法: python scan_full_quality.py [--ep P01 ...]
"""
import json
import os
import re
import sys

import cv2
import numpy as np
from opencc import OpenCC

from rapidocr import RapidOCR

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
VIDEO_DIR = os.path.join(BASE, 'Videos')
SUBTITLE_AREA = (100, 895, 1820, 985)
MATCH_AUTO = 0.90
MATCH_CAND = 0.40
MAX_LEN_DIFF = 2
OFFSET_MS = 800

cc = OpenCC('t2s')
CJK_RE = re.compile(r'[\u4e00-\u9fff]')
PUNCT_RE = re.compile(r'[，。！？、：；“”‘’《》—…\u3000]')
NOISE_WORDS = ('bilibili', 'lipilibili', 'shou', 'no.3', '正版', '正饭', '正服', '脂版', '脂',
               '張', '張', '一集', '登出')


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def lcs(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i][j - 1], dp[i - 1][j])
    return dp[m][n]


def ratio(a, b):
    return lcs(a, b) / min(len(a), len(b)) if a and b else 0


def to_cjk(t):
    """简繁归一 + 仅保留汉字"""
    s = cc.convert(t)
    return ''.join(CJK_RE.findall(s))


def denoise(t):
    """简繁归一 + 去噪音词 + 保留汉字与中文标点，清理空白"""
    s = cc.convert(t)
    for w in NOISE_WORDS:
        s = s.replace(w, '')
    s = ''.join(ch for ch in s if CJK_RE.search(ch) or PUNCT_RE.search(ch))
    return re.sub(r'\s+', '', s).strip()


def main():
    eps = []
    args = sys.argv[1:]
    while args:
        a = args.pop(0)
        if a == '--ep' and args:
            eps.append(args.pop(0))
    ocr = RapidOCR(params={'EngineConfig.onnxruntime.use_cuda': True})
    print('v5/v6 server GPU 就绪', flush=True)

    applied, candidates, skipped_n = [], [], 0
    for fname in sorted(os.listdir(CLEAN_DIR)):
        if not fname.endswith('.json'):
            continue
        ep = fname.split(']')[0].lstrip('[')
        if eps and ep not in eps:
            continue
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            continue
        data = json.load(open(os.path.join(CLEAN_DIR, fname), encoding='utf-8'))
        cap = cv2.VideoCapture(video[0])
        ep_a = ep_c = 0
        for r in data:
            text = r.get('text', '').strip()
            sec = parse_ts(r.get('timestamp', ''))
            if not text or sec is None:
                continue
            cap.set(cv2.CAP_PROP_POS_MSEC, int(sec * 1000 + OFFSET_MS))
            ret, frame = cap.read()
            if frame is None:
                continue
            crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3],
                         SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
            res = ocr(crop)
            otxt = ''.join(res.txts) if res.txts else ''
            if not otxt:
                # 空结果补反色二值化通道
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                _, b = cv2.threshold(255 - gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                res2 = ocr(cv2.cvtColor(b, cv2.COLOR_GRAY2BGR))
                otxt = ''.join(res2.txts) if res2.txts else ''
            if not otxt:
                continue
            lc = to_cjk(text)
            new_txt = denoise(otxt)
            oc_c = to_cjk(new_txt)
            if not lc or not oc_c:
                continue
            rr = ratio(lc, oc_c)
            if rr >= MATCH_AUTO and abs(len(oc_c) - len(lc)) <= MAX_LEN_DIFF:
                if new_txt and new_txt != text:
                    r['text'] = new_txt
                    applied.append({'ep': ep, 'ts': r.get('timestamp'),
                                    'from': text[:40], 'to': new_txt[:40],
                                    'ratio': round(rr, 3)})
                    ep_a += 1
            elif rr >= MATCH_CAND:
                candidates.append({'ep': ep, 'ts': r.get('timestamp'),
                                   'lib': text[:40], 'ocr': otxt[:40],
                                   'ratio': round(rr, 3)})
                ep_c += 1
            else:
                skipped_n += 1
        cap.release()
        json.dump(data, open(os.path.join(CLEAN_DIR, fname), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(f'{ep}: 应用 {ep_a} | 候选 {ep_c} | 跳过/未读 {len(data) - ep_a - ep_c}',
              flush=True)

    with open(os.path.join(BASE, 'review', 'ocr_revision_applied.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(applied, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(BASE, 'review', 'ocr_revision_candidates.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(candidates, fh, ensure_ascii=False, indent=1)
    print(f'\n总计: 自动修正 {len(applied)} | 候选待核 {len(candidates)} | 无关/未读 {skipped_n}')
    print('审计: review/ocr_revision_applied.json / ocr_revision_candidates.json')


if __name__ == '__main__':
    main()
