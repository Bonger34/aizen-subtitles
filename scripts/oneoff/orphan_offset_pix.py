# -*- coding: utf-8 -*-
"""孤儿帧 vs 库内同文本条目配图 的像素比对。

目的: 判定"孤儿帧"是否只是【同一张图被记到了另一秒】(命名/时间戳偏移),
     还是【库里真的没有的独立画面】。
判据: 平均绝对差 MAD < 3 视为同一张图。
"""
import json
import os
import re
import collections

import cv2
import numpy as np

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'docs', 'frames')
CLEAN = os.path.join(B, 'subtitle_clean')
fm = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
MAP = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])
ocr = json.load(open(os.path.join(B, 'review', 'orphan_ocr.json'), encoding='utf-8'))

# 库: (ep, sec) -> 文本 ; ep -> [(sec, text)]
lib, lib_by_sec = collections.defaultdict(list), {}
for fn in os.listdir(CLEAN):
    mm = re.match(r'\[(P\d+)\]', fn)
    if not mm:
        continue
    ep = mm.group(1)
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        t = re.match(r'(\d+)m(\d+)s', e.get('timestamp') or '')
        txt = ''.join(re.findall(r'[\u4e00-\u9fff]', e.get('text') or ''))
        if t and txt:
            sec = int(t.group(1)) * 60 + int(t.group(2))
            lib[ep].append((sec, txt))
            lib_by_sec[(ep, e['timestamp'])] = txt

# 帧名 -> 该帧在 map 中被哪个 key 引用
frame_of_key = MAP


def bef(tn, w):
    return sum(1 for c in tn if c in w) / len(tn) if tn and w else 0.0


def gray(p):
    img = cv2.imread(p)
    return None if img is None else cv2.cvtColor(cv2.resize(img, (240, 135)), cv2.COLOR_BGR2GRAY).astype(np.int16)


def name_sec(fn):
    mm = re.match(r'P(\d+)_(\d+)m(\d+)s', fn)
    return None if not mm else int(mm.group(2)) * 60 + int(mm.group(3))


rows = []
for tag in ('A', 'B'):
    for x in ocr[tag]:
        tn = x['ocr']
        if len(tn) < 2:
            continue
        ep = x['f'][:3]
        sec = name_sec(x['f'])
        top, arg = 0.0, None
        for s, t in lib.get(ep, []):
            v = bef(tn, t)
            if v > top:
                top, arg = v, (s, t)
        if top < 0.7 or arg is None:
            continue
        off = None if sec is None else arg[0] - sec
        rows.append({'f': x['f'], 'tag': tag, 'ep': ep, 'sec': sec, 'text': tn,
                     'lib_sec': arg[0], 'lib_text': arg[1], 'score': round(top, 2), 'off': off})

# 对有偏移的配对做像素比对
pairs = [r for r in rows if r['off'] not in (None, 0)]
lines = [f'文本匹配到的孤儿帧 {len(rows)} 条; 其中库内秒与帧名不一致 {len(pairs)} 条']
offs = collections.Counter(r['off'] for r in pairs)
lines.append('偏移分布(库秒 - 帧秒): ' + ', '.join(f'{k:+d}s×{v}' for k, v in sorted(offs.items())))

same_cnt = 0
for r in sorted(pairs, key=lambda y: -abs(y['off'])):
    key = f"[{r['ep']}]{r['ep'][1:]} {r['lib_text']}|{r['lib_sec'] // 60}m{r['lib_sec'] % 60:02d}s"
    cand = [v for k, v in MAP.items() if k.startswith(f"[{r['ep']}]") and k.endswith(f"|{r['lib_sec'] // 60}m{r['lib_sec'] % 60:02d}s")]
    mapped = cand[0] if cand else None
    a = gray(os.path.join(FR, r['f']))
    b = gray(os.path.join(FR, mapped)) if mapped else None
    if a is None or b is None:
        mad = None
    else:
        mad = float(np.abs(a - b).mean())
    if mad is not None and mad < 3:
        same_cnt += 1
    r['mapped'] = mapped
    r['mad'] = None if mad is None else round(mad, 2)
    lines.append(f"  {r['f']:16s} off={r['off']:+4d}s lib={r['lib_sec'] // 60}m{r['lib_sec'] % 60:02d}s "
                 f"mapped={mapped} MAD={r['mad']} ocr=[{r['text'][:22]}] lib=[{r['lib_text'][:22]}]")
lines.insert(2, f'像素比对: MAD<3(同一张图) {same_cnt} / {len(pairs)}')

txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'orphan_offset_pix.txt'), 'w', encoding='utf-8').write(txt)
print(txt[:6000])
