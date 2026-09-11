# -*- coding: utf-8 -*-
"""定向重 OCR: 对库中"文本很短(疑似被裁切的碎片)"的条目, 用加高裁剪区 y 850~1075 重读。

更换规则(保守): 新文本更长 且 旧文本 ≥80% 被新文本包含 -> 判为"补全", 建议替换。
其余变化只记录供人工判断。

用法: python reocr_short.py [最大字数, 默认4] [--apply]
"""
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
import numpy as np
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'Web', 'frames')
CLEAN = os.path.join(B, 'subtitle_clean')
CROP = (100, 850, 1820, 1075)
OUT = os.path.join(B, 'review', 'reocr_short.json')
LIM = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4
APPLY = '--apply' in sys.argv


def norm(s):
    return ''.join(re.findall(r'[\u4e00-\u9fff0-9A-Za-z]', s or ''))


def main():
    MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                               open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read(),
                               re.S).group(1))
    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
    })
    # 收集目标: (集, 文件, 文本长度<=LIM 的条目)
    todo = []
    for fn in sorted(os.listdir(CLEAN)):
        if not fn.endswith('.json'):
            continue
        title = fn[:-5]
        data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
        for e in data:
            if len(norm(e.get('text'))) <= LIM:
                f = MAP.get(f'{title}|{e["timestamp"]}')
                if f and os.path.exists(os.path.join(FR, f)):
                    todo.append((title, e, f))
    print(f'目标条目 {len(todo)} 条(文本长度<={LIM})', flush=True)

    out = {'limit': LIM, 'total': len(todo), 'fix': [], 'diff': []}
    for i, (title, e, f) in enumerate(todo):
        if i % 100 == 0:
            print(f'  {i}/{len(todo)}', flush=True)
        img = cv2.imread(os.path.join(FR, f))
        if img is None:
            continue
        h, w = img.shape[:2]
        sy = h / 1080.0
        c = img[int(CROP[1] * sy):int(CROP[3] * sy), int(CROP[0] * (w / 1920.0)):int(CROP[2] * (w / 1920.0))]
        c = cv2.resize(c, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
        arr = c.copy()
        m = np.all(arr > 245, axis=2)
        arr[m] = [255, 255, 255]
        arr[~m] = [0, 0, 0]
        try:
            res = ocr(arr)
        except Exception:
            continue
        new = norm(''.join(res.txts) if res.txts else '')
        old = norm(e.get('text'))
        if not new or new == old:
            continue
        cont = sum(1 for ch in old if ch in new) / len(old) if old else 0
        rec = {'title': title, 'ts': e['timestamp'], 'frame': f, 'old': old, 'new': new,
               'cont': round(cont, 2)}
        if len(new) > len(old) and cont >= 0.8:
            out['fix'].append(rec)
            if APPLY:
                e['text'] = new
        else:
            out['diff'].append(rec)
    if APPLY:
        for fn in sorted(os.listdir(CLEAN)):
            if fn.endswith('.json'):
                pass
        # 按集回写
        byt = {}
        for r in out['fix']:
            byt.setdefault(r['title'], {})[r['ts']] = r['new']
        for title, mp in byt.items():
            p = os.path.join(CLEAN, title + '.json')
            data = json.load(open(p, encoding='utf-8'))
            for e in data:
                if e['timestamp'] in mp:
                    e['text'] = mp[e['timestamp']]
            json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    lines = [f"重 OCR(裁剪 y {CROP[1]}~{CROP[3]}) 目标 {len(todo)} 条: 补全 {len(out['fix'])} / 其他变化 {len(out['diff'])}"
             + ('(已落盘)' if APPLY else '(预演)'), '', '补全样例:']
    for r in out['fix'][:40]:
        lines.append(f"  {r['title']} {r['ts']:>7s} [{r['old']}] -> [{r['new']}]")
    lines.append('')
    lines.append('其他变化(需人工判断)样例:')
    for r in out['diff'][:40]:
        lines.append(f"  {r['title']} {r['ts']:>7s} [{r['old']}] vs [{r['new']}]")
    txt = '\n'.join(lines)
    open(os.path.join(B, 'review', 'reocr_short.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
