# -*- coding: utf-8 -*-
"""calibrate_ts.py — 阶段3：字幕时间戳校准分析（先分析后应用）

原理：v5/VL 的 ts 是"抽取窗口"代表值，可能与字幕真实显示时刻差 ±1~3s。
对每条：ts±2s 共 5 帧 rapidocr 扫描字幕区 → 原文本 LCS 匹配度：
  - 若某偏移帧匹配度显著更高（>=0.5 且优于 ts 基准 +0.2）且 |Δt|>=1 → 校准候选
输出：review/ts_calibration_[EP].json（候选与偏移分布），默认不修改数据。

用法: python calibrate_ts.py --ep P01 [--apply]
"""
import json
import os
import re
import sys

import cv2
from rapidocr_onnxruntime import RapidOCR

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
VIDEO_DIR = os.path.join(BASE, 'Videos')
SUBTITLE_AREA = (100, 895, 1820, 985)
RANGES = (-2, -1, 0, 1, 2)   # ts±2s 扫描窗口
MIN_GAIN = 0.2               # 匹配度需比基准高 0.2 才校准
MIN_OFF = 1                  # 至少偏移 1s


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


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
    if not a or not b:
        return 0
    return lcs(a, b) / min(len(a), len(b))


def dedup(data):
    """校准后清理：按时间排序，同文本且 ts 差 <=3s 保留更早一条"""
    data.sort(key=lambda r: parse_ts(r.get('timestamp', '')) or 0)
    out = []
    for r in data:
        dup = False
        for o in out[-4:]:
            if o.get('text', '') and o.get('text') == r.get('text') and \
               abs((parse_ts(o.get('timestamp', '')) or 0) - (parse_ts(r.get('timestamp', '')) or 0)) <= 3:
                dup = True
                break
        if not dup:
            out.append(r)
    return out


def main():
    args = sys.argv[1:]
    apply = '--apply' in args
    ep = args[args.index('--ep') + 1] if '--ep' in args else None

    ocr = RapidOCR()
    out_report = []
    for fname in sorted(os.listdir(CLEAN_DIR)):
        if not fname.endswith('.json'):
            continue
        e = fname.split(']')[0].lstrip('[')
        if ep and e != ep:
            continue
        data = json.load(open(os.path.join(CLEAN_DIR, fname), encoding='utf-8'))
        video = ''
        for vf in sorted(os.listdir(VIDEO_DIR)):
            if vf.startswith(f'[{e}]') and vf.lower().endswith('.mp4'):
                video = os.path.join(VIDEO_DIR, vf)
                break
        cap = cv2.VideoCapture(video)
        n_cand = 0
        cands = []
        applied = []
        for r in data:
            text = r.get('text', '').strip()
            sec = parse_ts(r.get('timestamp', ''))
            if not text or sec is None or len(text) < 4:
                continue
            scores = {}
            for off in RANGES:
                t = sec + off
                if t < 0:
                    continue
                cap.set(cv2.CAP_PROP_POS_MSEC, int(t * 1000 + 800))
                ok, frame = cap.read()
                if not ok or frame is None:
                    scores[off] = 0
                    continue
                crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
                result, _ = ocr(crop)
                texts = [x[1] for x in result] if result else []
                scores[off] = max((ratio(text, x) for x in texts), default=0)
            base = scores.get(0, 0)
            best_off, best_s = max(scores.items(), key=lambda kv: kv[1])
            if best_s >= 0.5 and abs(best_off) >= MIN_OFF and best_s >= base + MIN_GAIN and base < 0.8:
                n_cand += 1
                cands.append({'ts': r['timestamp'], 'new_ts': ts_str(sec + best_off),
                              'base': round(base, 2), 'best': round(best_s, 2), 'off': best_off,
                              'text': text})
                if apply:
                    r['timestamp'] = ts_str(sec + best_off)
                    applied.append(cands[-1])
        cap.release()
        if apply:
            n_before = len(data)
            data = dedup(data)
            path = os.path.join(CLEAN_DIR, fname)
            json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(f'{e}: 校准 {len(applied)} 条 ts，去重后 {n_before}->{len(data)} 条')
        else:
            print(f'{e}: 扫描 {len(data)} 条，校准候选 {n_cand} 条')
            for c in cands[:15]:
                print(f"   {c['ts']} → {c['new_ts']} (base={c['base']:.2f} best={c['best']:.2f}) 「{c['text'][:24]}」")
        out_report.append({'ep': e, 'candidates': cands})
    json.dump(out_report, open(os.path.join(BASE, 'review', f'ts_calibration_{ep or "ALL"}.json'),
                               'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    if apply:
        print(f'审计: review/ts_calibration_{ep or "ALL"}.json（{sum(len(x["candidates"]) for x in out_report)} 条校准）')


if __name__ == '__main__':
    main()
