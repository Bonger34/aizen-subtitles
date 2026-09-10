# -*- coding: utf-8 -*-
"""孤儿帧体检:统计字幕带白色像素比,并与字幕库对照。
输出 review/orphan_scan.json + 控制组阈值建议。
"""
import os, re, json, random
import numpy as np
import cv2

ROOT = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
WEB = os.path.join(ROOT, 'Web')
FRAMES = os.path.join(WEB, 'frames')
CLEAN = os.path.join(ROOT, 'subtitle_clean')
OUT = os.path.join(ROOT, 'review', 'orphan_scan.json')
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# ---------- 1. 载入 frames_map,求差集 ----------
fm = open(os.path.join(WEB, 'frames_map.js'), encoding='utf-8').read()
m = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])
ref = {v for v in m.values() if isinstance(v, str)}
files = set(os.listdir(FRAMES))
orphans = sorted(files - ref)
print(f'映射 {len(m)} 条 / 被引用帧 {len(ref)} / 磁盘帧 {len(files)} / 孤儿 {len(orphans)}')


# ---------- 2. 载入字幕库(按集索引) ----------
lib = {}          # ep -> [(ts_sec, text), ...]
for fn in os.listdir(CLEAN):
    mm = re.match(r'\[P(\d+)\]', fn)
    if not mm:
        continue
    ep = int(mm.group(1))
    data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
    rows = []
    for it in data:
        ts = it.get('timestamp') or it.get('ts') or it.get('time') or ''
        t = it.get('text') or it.get('txt') or ''
        ms = re.match(r'(\d+)m(\d+)s', str(ts))
        if ms:
            rows.append((int(ms.group(1)) * 60 + int(ms.group(2)), t))
    lib[ep] = sorted(rows)
print('库集数', len(lib), '总条数', sum(len(v) for v in lib.values()))


def name_sec(fn):
    mm = re.match(r'P(\d+)_(\d+)m(\d+)s\.jpg', fn)
    if not mm:
        return None, None
    return int(mm.group(1)), int(mm.group(2)) * 60 + int(mm.group(3))


# ---------- 3. 白色像素比:控制组 vs 孤儿 ----------
def white_ratio(path):
    img = cv2.imread(path)
    if img is None:
        return None
    h, w = img.shape[:2]
    sx, sy = w / 1920.0, h / 1080.0
    x0, y0, x1, y1 = int(100 * sx), int(895 * sy), int(1820 * sx), int(985 * sy)
    band = img[y0:y1, x0:x1]
    b, g, r = band[:, :, 0].astype(np.int16), band[:, :, 1].astype(np.int16), band[:, :, 2].astype(np.int16)
    # 近白判据:三通道都高且互相接近(避免纯色块误判)
    mx = np.maximum(np.maximum(b, g), r)
    mn = np.minimum(np.minimum(b, g), r)
    mask = (mn > 225) & ((mx - mn) < 25)
    return float(mask.mean())


ctrl = random.Random(7).sample(sorted(ref), 400)
ctrl_wr = [(f, white_ratio(os.path.join(FRAMES, f))) for f in ctrl]
ctrl_wr = [(f, v) for f, v in ctrl_wr if v is not None]
vals = sorted(v for _, v in ctrl_wr)
print('控制组(确定有字幕) wr 分位:',
      {p: round(vals[int(len(vals) * p / 100)], 4) for p in (0, 1, 5, 10, 25, 50)})

# 阈值取控制组 1% 分位的一半,保守判定"可能有字幕"
thr = max(0.002, vals[max(0, int(len(vals) * 0.01))] * 0.5)
print('判定阈值 thr =', round(thr, 5))

recs = []
exact, near_only, none = [], [], []
for i, fn in enumerate(orphans):
    v = white_ratio(os.path.join(FRAMES, fn))
    ep, sec = name_sec(fn)
    same, near = [], []
    if ep in lib and sec is not None:
        same = [t for ts, t in lib[ep] if ts == sec]
        near = [t for ts, t in lib[ep] if abs(ts - sec) <= 2]
    recs.append({'f': fn, 'ep': ep, 'sec': sec, 'wr': v,
                 'has_sub': (v is not None and v >= thr), 'same': same, 'near': near})
    (exact if same else (near_only if near else none)).append(fn)

wr_all = sorted(r['wr'] for r in recs if r['wr'] is not None)
q = lambda p: round(wr_all[min(len(wr_all) - 1, int(len(wr_all) * p / 100))], 4)
print('孤儿 wr 分位:', {p: q(p) for p in (0, 1, 5, 25, 50, 95, 100)})
print(f'孤儿 {len(recs)}:该秒库内已有条目 {len(exact)} / 仅±2s内有 {len(near_only)} / ±2s内全无 {len(none)}')
print('  样例(±2s内全无):', none[:10])
json.dump({'thr': thr, 'ctrl_p1': vals[max(0, int(len(vals) * 0.01))], 'recs': recs},
          open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('写出', OUT)
