# -*- coding: utf-8 -*-
"""q_scan_ep.py — 单集原帧重 OCR: 顺序读 1080p 视频, 对每条目取 3 帧, 按文字行分段识别。

为什么要走原帧: 库文本由 CutSubtitle_rapidocr.py 用 1080p 原帧 + 固定窄带(895~985) 生成;
Web/frames 只有 960x540 且经过 JPEG 压缩, 分辨率不足; 而实测 28.6% 帧的文字行下缘伸出窄带,
所以重扫必须同时提升"分辨率"和"裁剪自适应"两点。

用法: python q_scan_ep.py P01 [P02 ...]
输出: review/q_scan_<EP>.json  (每集一个)
"""
import json
import os
import re
import sys
import time

import cv2

from q_common import (SCAN_TOP, SCAN_BOT, X0, X1, PAD_Y, build_engine, crop_norm,
                      ocr_text, split_lines, gray_white)

B = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle_clean')
OUT_DIR = os.path.join(B, 'review')
OFFSETS = (0.0, 0.25, 0.5)   # 相对条目时间戳的取帧偏移(秒)


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9A-Za-z]', s or ''))


def sim(a, b):
    """字符级相似度: 1 - 归一化编辑距离(与全库其它脚本口径一致: min 长度归一)。"""
    a, b = norm(a), norm(b)
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


def seg_info(img, y0, y1):
    """段的水平范围与居中程度 —— 字幕居中且不横跨全宽, 演职员表横跨两侧。"""
    h, w = img.shape[:2]
    sy = h / 1080.0
    sub = img[max(0, int((y0 - 2) * sy)):min(h, int((y1 + 2) * sy))]
    m = gray_white(sub)
    cols = m.sum(axis=0)
    nz = [i for i, v in enumerate(cols) if v > 0]
    if not nz:
        return None
    x0, x1 = nz[0] * 1920.0 / w, (nz[-1] + 1) * 1920.0 / w
    return {'x0': round(x0), 'x1': round(x1), 'width': round(x1 - x0),
            'center_off': round(abs((x0 + x1) / 2 - 960)), 'px': int(m.sum())}


def scan_ep(ocr, ep):
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]
    title = fn[:-5]
    data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # 目标帧号 -> [(条目下标, 偏移序号)]
    want = {}
    for i, e in enumerate(data):
        sec = parse_ts(e.get('timestamp'))
        if sec is None:
            continue
        for k, off in enumerate(OFFSETS):
            fno = min(total - 1, max(0, int(round((sec + off) * fps))))
            want.setdefault(fno, []).append((i, k))

    items = [{'ts': e.get('timestamp'), 'old': e.get('text'), 'frames': [None] * len(OFFSETS)}
             for e in data]
    t_read = t_ocr = 0.0
    n = 0
    t0 = time.time()
    for fno in sorted(want):
        while n < fno:
            cap.grab()
            n += 1
        ta = time.time()
        ok, frame = cap.read()
        n += 1
        t_read += time.time() - ta
        if not ok or frame is None:
            continue
        segs = split_lines(frame, SCAN_TOP, SCAN_BOT)
        if not segs:
            for i, k in want[fno]:
                items[i]['frames'][k] = {'fno': fno, 'segs': []}
            continue
        # 按白像素密度降序识别, 最多 4 段; 用该帧首个关联条目的旧文本做提前退出判据
        probe = data[want[fno][0][0]].get('text', '')
        order = sorted(range(len(segs)), key=lambda j: -segs[j][2])
        recs = []
        for j in order[:4]:
            y0, y1 = segs[j][0], segs[j][1]
            crop = crop_norm(frame, (X0, y0 - PAD_Y, X1, y1 + PAD_Y), upscale=1.0)
            tb = time.time()
            txt = ocr_text(ocr, crop)
            t_ocr += time.time() - tb
            if not txt:
                continue
            recs.append({'y0': y0, 'y1': y1, 'fill': segs[j][2], 'text': txt,
                         'geom': seg_info(frame, y0, y1)})
            if sim(txt, probe) >= 0.98:
                break
        for i, k in want[fno]:
            old = data[i].get('text', '')
            recs_i = [dict(r, sim_old=round(sim(r['text'], old), 3)) for r in recs]
            items[i]['frames'][k] = {
                'fno': fno, 'segs': recs_i,
                'best': max(recs_i, key=lambda r: r['sim_old']) if recs_i else None}
    cap.release()
    el = time.time() - t0
    out = {'ep': ep, 'title': title, 'fps': round(fps, 4), 'frames_total': total,
           'n_entries': len(data), 'n_targets': len(want), 'elapsed': round(el, 1),
           'elapsed_read': round(t_read, 1), 'elapsed_ocr': round(t_ocr, 1), 'items': items}
    json.dump(out, open(os.path.join(OUT_DIR, f'q_scan_{ep}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    n_same = sum(1 for it in items if it['frames'][1] and it['frames'][1]['best']
                 and it['frames'][1]['best']['sim_old'] >= 0.95)
    print(f'{ep}: {len(data)} 条 / 目标帧 {len(want)} / 用时 {el:.1f}s(读 {t_read:.1f} OCR {t_ocr:.1f}) '
          f'/ 中帧高相似 {n_same}', flush=True)
    return out


def main():
    eps = [a for a in sys.argv[1:] if not a.startswith('-')] or ['P01']
    ocr = build_engine()
    print('RapidOCR(PPOCRV6 MEDIUM, 1080p 原帧) 就绪', flush=True)
    for ep in eps:
        scan_ep(ocr, ep)


if __name__ == '__main__':
    main()
