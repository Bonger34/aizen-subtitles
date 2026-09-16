# -*- coding: utf-8 -*-
"""fix_noise_entries.py — 修复 51 条水印/日文残留条目

对 ocr_p01p03_needs.json 条目：3 帧采样（ts-0.3/+0.8/+1.8s）字幕带 v5 重读，
denoise 后：无日文假名且汉字>=4 → 重写库文本；否则保留原样转候选。
"""
import json
import os
import re

import cv2

from rapidocr import RapidOCR
from opencc import OpenCC

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
VIDEO_DIR = os.path.join(BASE, 'Videos')
SUBTITLE_AREA = (100, 895, 1820, 985)
NEEDS = os.path.join(BASE, 'review', 'ocr_p01p03_needs.json')
MAX_LEN_DIFF = 2

cc = OpenCC('t2s')
CJK_RE = re.compile(r'[\u4e00-\u9fff]')
KANA_RE = re.compile(r'[\u3040-\u30ff]')
PUNCT_RE = re.compile(r'[，。！？、：；“”‘’《》—…\u3000]')
NOISE_WORDS = ('bilibili', 'lipilibili', 'shou', '正版', '正饭', '正服', '脂', '張',
               'Magnetic', 'No.3', '閲覧', '注意', 'RCER')


def denoise(t):
    s = cc.convert(t)
    for w in NOISE_WORDS:
        s = s.replace(w, '')
    s = ''.join(ch for ch in s if CJK_RE.search(ch) or PUNCT_RE.search(ch))
    return re.sub(r'\s+', '', s).strip()


def scan_noise():
    """重新扫描全库水印/日文残留条目（ep 用 P01 格式）"""
    bad_chars = ('批井', '备位', '不子', '目快乐', '生自', '正版', '正饭', '正服', '脂版',
                 'MSelect', 'クワトロ', 'TURBINE', 'Lilbi', 'bilibil', '円谷',
                 'テレビ', 'の', 'は', 'を', 'お', 'ぐ', 'し', 'て', 'れ', 'ン', 'ー')
    needs = []
    for fname in sorted(os.listdir(CLEAN_DIR)):
        if not fname.endswith('.json'):
            continue
        ep = os.path.basename(fname)[1:4]   # P01
        d = json.load(open(os.path.join(CLEAN_DIR, fname), encoding='utf-8'))
        for r in d:
            t = r.get('text', '')
            if any(b in t for b in bad_chars):
                needs.append({'ep': ep, 'ts': r.get('timestamp'), 'text': t[:40]})
    return needs


def main():
    meta = scan_noise()
    needs = []
    seen = set()
    for x in meta:
        k = (x['ep'], x['ts'])
        if k not in seen:
            seen.add(k)
            needs.append(x)
    print(f'扫描残留 {len(needs)} 条', flush=True)
    ocr = RapidOCR(params={'EngineConfig.onnxruntime.use_cuda': True})

    # 预分组
    by_ep = {}
    for x in needs:
        by_ep.setdefault(x['ep'], []).append(x)

    fixed, still = [], []
    for ep, items in by_ep.items():
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            continue
        fs = [f for f in os.listdir(CLEAN_DIR) if f.startswith(f'[{ep}]') and f.endswith('.json')]
        data = json.load(open(os.path.join(CLEAN_DIR, fs[0]), encoding='utf-8'))
        by_ts = {x['ts']: x for x in items}
        cap = cv2.VideoCapture(video[0])
        for r in data:
            ts = r.get('timestamp')
            if ts not in by_ts:
                continue
            sec_n = int(ts.rstrip('s').split('m')[0]) * 60 + int(ts.split('m')[1].rstrip('s'))
            best = ''
            for off_ms in (-300, 800, 1800):
                cap.set(cv2.CAP_PROP_POS_MSEC, int(sec_n * 1000 + off_ms))
                ret, frame = cap.read()
                if frame is None:
                    continue
                crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3],
                             SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
                res = ocr(crop)
                t = ''.join(res.txts) if res.txts else ''
                if t:
                    d = denoise(t)
                    if len(CJK_RE.findall(d)) > len(CJK_RE.findall(best)):
                        best = d
            if best and len(CJK_RE.findall(best)) >= 4 and not KANA_RE.search(best):
                r['text'] = best
                fixed.append({'ep': ep, 'ts': ts, 'text': best})
            else:
                still.append({'ep': ep, 'ts': ts, 'text': r.get('text', '')[:40],
                              'reason': 'kana_or_short' if best else 'no_read'})
        cap.release()
        json.dump(data, open(os.path.join(CLEAN_DIR, fs[0]), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(f'{ep}: 修复 {len([x for x in fixed if x["ep"] == ep])}', flush=True)

    with open(os.path.join(BASE, 'review', 'ocr_noise_fixed.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(fixed, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(BASE, 'review', 'ocr_noise_still.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(still, fh, ensure_ascii=False, indent=1)
    print(f'\n修复 {len(fixed)} | 保留候选 {len(still)}')


if __name__ == '__main__':
    main()
