# -*- coding: utf-8 -*-
"""q_reframe_compare.py — 生成"旧帧图 vs 新帧图"对照表, 用于确认帧图重抽是否修对了。

用法: python q_reframe_compare.py P07:2m31s P11:6m53s P16:9m27s ...
输出: review/q_reframe_compare_<k>.jpg
"""
import json
import os
import re
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
FR = os.path.join(B, 'docs', 'frames')
FIX = os.path.join(B, 'docs', 'frames_fix')
FONTS = [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf']
ROW_H = 300


def font(sz):
    for f in FONTS:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    args = sys.argv[1:]
    M = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                             open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read(),
                             re.S).group(1))
    lib = {}
    for f in sorted(os.listdir(os.path.join(B, 'subtitle_clean'))):
        if not (f.endswith('.json') and re.match(r'^\[P\d+\]', f)):
            continue
        ep = re.search(r'\[(P\d+)\]', f).group(1)
        for e in json.load(open(os.path.join(B, 'subtitle_clean', f), encoding='utf-8')):
            lib[(ep, e.get('timestamp'))] = e.get('text', '')
    keys = [(a.split(':')[0], a.split(':')[1]) for a in args]
    f1, f2 = font(24), font(20)
    im = Image.new('RGB', (1560, len(keys) * ROW_H), (24, 24, 24))
    dr = ImageDraw.Draw(im)
    for i, (ep, ts) in enumerate(keys):
        y = i * ROW_H
        name = M.get(next((k for k in M if k.endswith('|' + ts) and k.startswith(f'[{ep}]')), ''))
        txt = lib.get((ep, ts), '')
        thumb_w = 640
        for j, (src, tag, col) in enumerate(((FR, '旧帧图', (255, 140, 140)),
                                             (FIX, '新帧图', (140, 255, 140)))):
            p = os.path.join(src, name) if name else None
            if p and os.path.exists(p):
                b = cv2.imread(p)
                b = cv2.resize(b, (thumb_w, int(b.shape[0] * thumb_w / b.shape[1])))
                im.paste(Image.fromarray(cv2.cvtColor(b, cv2.COLOR_BGR2RGB)),
                         (8 + j * (thumb_w + 12), y + 30))
            dr.text((8 + j * (thumb_w + 12), y + 4), f'{i + 1}.{tag} {name}', font=f2, fill=col)
        dr.text((8, y + 264), f'{ep} {ts}  库文本: {txt[:40]}', font=f1, fill=(255, 220, 120))
        dr.line([(0, y + ROW_H - 1), (1560, y + ROW_H - 1)], fill=(90, 90, 90), width=1)
    out = os.path.join(REVIEW, 'q_reframe_compare.jpg')
    im.save(out, quality=92)
    print('saved', out)


if __name__ == '__main__':
    main()
