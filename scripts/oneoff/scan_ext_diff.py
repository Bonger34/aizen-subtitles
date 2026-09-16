# -*- coding: utf-8 -*-
"""三区域字幕检测对比(单遍读完, 只做检测, 不存帧不 OCR):
  BAND = 现有字幕带 (100,895,1820,985)
  LOW  = 带下方新增 (100,985,1820,1062)  <- 偏低的对白字幕会落到这里
  TOP  = 画面顶部  (100, 62,1820,200)    <- 预告卡/新闻画面的中文字幕(非台词, 仅统计)

判据与 scan_cont.py 一致: 灰度>245 占比, ON=0.02 / OFF=0.01 滞后状态机。
输出"仅 LOW 有 / 仅 TOP 有"的区间 —— 即现有扫描完全没覆盖的部分。
"""
import json
import os
import sys

import cv2

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
OUT = os.path.join(B, 'review', 'ext_regions')
os.makedirs(OUT, exist_ok=True)
ON_TH, OFF_TH = 0.02, 0.01
REGIONS = {'BAND': (100, 895, 1820, 985), 'LOW': (100, 985, 1820, 1062),
           'TOP': (100, 62, 1820, 200)}
STEP = 2


def scan(path):
    """单遍顺序读, 同时维护三个区域的状态机。"""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
    st = {k: {'state': 'off', 'start': None, 'peak': None, 'pr': 0.0, 'out': []} for k in REGIONS}
    n = 0
    while True:
        ret = cap.grab()
        if not ret:
            break
        n += 1
        if n % STEP:
            continue
        ret, frame = cap.retrieve()
        if not ret:
            continue
        sec = n / fps
        for k, box in REGIONS.items():
            gray = cv2.cvtColor(frame[box[1]:box[3], box[0]:box[2]], cv2.COLOR_BGR2GRAY)
            wr = float((gray > 245).mean())
            s = st[k]
            if s['state'] == 'off':
                if wr > ON_TH:
                    s.update(state='on', start=sec, peak=sec, pr=wr)
            else:
                if wr > s['pr']:
                    s['pr'], s['peak'] = wr, sec
                if wr < OFF_TH:
                    s['out'].append((round(s['start'], 1), round(sec, 1), round(s['pr'], 3)))
                    s.update(state='off', start=None, peak=None, pr=0.0)
    for k, s in st.items():
        if s['state'] == 'on':
            s['out'].append((round(s['start'], 1), round(n / fps, 1), round(s['pr'], 3)))
    cap.release()
    return {k: s['out'] for k, s in st.items()}


def overlap(a, b):
    return not (a[1] < b[0] or a[0] > b[1])


def main():
    eps = sys.argv[1:] or [f'P{i:02d}' for i in range(1, 26)]
    summary = []
    for ep in eps:
        path = None
        for f in os.listdir(V):
            if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
                path = os.path.join(V, f)
        if not path:
            continue
        got = scan(path)
        low_only = [x for x in got['LOW'] if not any(overlap(x, y) for y in got['BAND'])]
        top_only = [x for x in got['TOP'] if not any(overlap(x, y) for y in got['BAND'])]
        dur = lambda lst: round(sum(b - a for a, b, _ in lst), 1)
        rec = {'ep': ep, 'regions': got, 'low_only': low_only, 'top_only': top_only,
               'low_only_sec': dur(low_only), 'top_only_sec': dur(top_only)}
        json.dump(rec, open(os.path.join(OUT, f'{ep}.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(f"{ep}: BAND {len(got['BAND'])}段/{dur(got['BAND'])}s | LOW {len(got['LOW'])}段/{dur(got['LOW'])}s | "
              f"仅LOW {len(low_only)}段/{dur(low_only)}s | 仅TOP {len(top_only)}段/{dur(top_only)}s", flush=True)
        summary.append(rec)
    print(f"\n合计: 仅LOW {sum(r['low_only_sec'] for r in summary)}s, 仅TOP {sum(r['top_only_sec'] for r in summary)}s")
    json.dump([{'ep': r['ep'], 'low_only_sec': r['low_only_sec'], 'top_only_sec': r['top_only_sec'],
                'low_only': r['low_only'], 'top_only': r['top_only']} for r in summary],
              open(os.path.join(OUT, '_summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
