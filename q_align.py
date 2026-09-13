# -*- coding: utf-8 -*-
"""q_align.py — 对账实验: 已存 Web 帧(搜索界面所见) 与 视频各时间点是否同一画面/同一句字幕。

动机: 重扫发现部分条目"视频 t+0.25s 处显示的是下一句", 必须区分两种成因:
  (a) 库时间戳与视频时间轴不同步  -> 帧图与文本仍一致, 只是取帧位置偏了;
  (b) 已存帧本身取在别的位置      -> 帧图与文本错配, 属于必须修的严重问题。
用法: python q_align.py P01 11m20s 11m21s 11m23s
输出: review/q_align_<EP>.jpg
"""
import json
import os
import re
import sys

import cv2
import numpy as np

B = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(B, 'Videos')
FR = os.path.join(B, 'Web', 'frames')
OFFS = (-0.25, 0.0, 0.25, 0.55)


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def band_of(img, h=None):
    """取 y820~1080 的对照带(按 1080 比例), 统一输出宽 1500。"""
    hh = img.shape[0]
    y0, y1 = int(820 * hh / 1080), hh
    b = img[y0:y1]
    return cv2.resize(b, (1500, max(1, int(b.shape[0] * 1500 / b.shape[1]))))


def main():
    ep, tss = sys.argv[1], sys.argv[2:]
    MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                               open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read(),
                               re.S).group(1))
    title = next(t for t in MAP if t.startswith(f'[{ep}]')).split('|')[0]
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)

    rows = []
    n = 0
    last = 0
    for ts in tss:
        sec = parse_ts(ts)
        web = cv2.imread(os.path.join(FR, MAP[f'{title}|{ts}']))
        if web is not None:
            t = band_of(web)
            cv2.putText(t, f'WEB {ts}', (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            rows.append(t)
        for off in OFFS:
            fno = max(0, int(round((sec + off) * fps)))
            if fno < last:
                continue
            while n < fno:
                cap.grab()
                n += 1
            ok, f = cap.read()
            n += 1
            last = n
            if not ok:
                continue
            t = band_of(f)
            d = (float(np.abs(cv2.resize(web, (1500, t.shape[0])).astype(np.int16)
                              - t.astype(np.int16)).mean()) if web is not None else -1)
            lab = f'VID {ts}{off:+.2f} diffW={d:.1f}'
            cv2.putText(t, lab.replace(' ', '_'), (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 255, 0), 2)
            rows.append(t)
            print(lab)
        rows.append(np.full((6, 1500, 3), 128, np.uint8))
    cap.release()
    if rows:
        cv2.imwrite(os.path.join(B, 'review', f'q_align_{ep}.jpg'), np.vstack(rows),
                    [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f'saved review/q_align_{ep}.jpg')


if __name__ == '__main__':
    main()
