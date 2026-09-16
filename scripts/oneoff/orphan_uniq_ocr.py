# -*- coding: utf-8 -*-
"""对 102 张"独有内容"孤儿帧中尚未 OCR 的 67 张补齐 OCR 并定性。"""
import json
import os
import re
import sys

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
_ORT124 = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124'
if os.path.isdir(_NV_DLL):
    os.add_dll_directory(_NV_DLL)
    os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
if os.path.isdir(_ORT124):
    sys.path.insert(0, _ORT124)

import cv2
from orphan_ocr import make_ocr, band, binarize, ocr_text, load_lib  # noqa: E402
from orphan_verdict import best  # noqa: E402

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'docs', 'frames')
todo = json.load(open(os.path.join(B, 'review', 'orphan_uniq_todo.json'), encoding='utf-8'))
ocr = make_ocr()
print('OCR 就绪, 待补', len(todo), flush=True)
lib = load_lib()
allrows = [(ep,) + r for ep, rows in lib.items() for r in rows]

JPN = re.compile(r'[\u3040-\u30ff]')
out = []
for i, fn in enumerate(todo):
    if i % 10 == 0:
        print(f'  {i}/{len(todo)}', flush=True)
    img = cv2.imread(os.path.join(FR, fn))
    if img is None:
        continue
    b = band(img)
    t245 = ocr_text(ocr, binarize(b, 245))[0]
    t200, raw = ocr_text(ocr, binarize(b, 200))
    tn = t200 if len(t200) > len(t245) else t245
    ep = fn[:3]
    sl, al = best(tn, lib.get(ep, [])) if tn else (0, None)
    sa, aa = best(tn, allrows) if tn else (0, None)
    if len(tn) < 2:
        v = '空或单字'
    elif sl >= 0.6:
        v = f'本集库已有({al[0] // 60}m{al[0] % 60:02d}s)'
    elif sa >= 0.6:
        v = f'全集库已有({aa[0]} {aa[1] // 60}m{aa[1] % 60:02d}s)'
    elif JPN.search(raw or ''):
        v = '日文文本'
    else:
        v = '待目视'
    out.append({'f': fn, 'ocr': tn, 'raw': raw, 'best_local': round(sl, 2),
                'best_all': round(sa, 2), 'verdict': v})
json.dump(out, open(os.path.join(B, 'review', 'orphan_uniq_ocr.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

lines = ['102 张独有内容孤儿帧 · 补齐 OCR 后的定性(仅列本次补的 67 张):']
for x in out:
    lines.append(f"  {x['f']:18s} [{x['verdict']:22s}] ocr=[{x['ocr']}] raw=[{(x['raw'] or '')[:44]}]")
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'orphan_uniq_report.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
