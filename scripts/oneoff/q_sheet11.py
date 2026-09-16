# -*- coding: utf-8 -*-
"""q_sheet10.py — 为"帧图显示的是别的句子"的残留条目生成**字幕带原尺寸**对照表。

为什么不用 q_sheet8/q_sheet9 那种整帧缩略图: 1560x3750 的表会被读图工具缩到 516x1240,
每行只有 ~83px, 字幕被压成 ~5px 完全读不出。本脚本只裁**字幕带**(960x540 帧的 y438~502)
并保持原尺寸贴出, 表自然很矮(每行 76px), 不会被缩 -> 字能读清。

用法: python q_sheet10.py [--per 10]
输出: review/q_sheet11_<k>.jpg
"""
import json
import os
import re
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
FR = os.path.join(B, 'docs', 'frames')
FONTS = [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf']
ROW_H = 78
BAND = (436, 504)      # 960x540 帧里的字幕带
LEFT = 620             # 左侧文本区宽度


def font(sz):
    for f in FONTS:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    per = 10
    if '--per' in sys.argv:
        per = int(sys.argv[sys.argv.index('--per') + 1])
    rows = json.load(open(os.path.join(REVIEW, 'q_fv2_review.json'), encoding='utf-8'))
    M = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                             open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read(),
                             re.S).group(1))
    f1, f2 = font(20), font(17)
    print(f'{len(rows)} 条')
    for k in range(0, len(rows), per):
        chunk = rows[k:k + per]
        im = Image.new('RGB', (LEFT + 960, len(chunk) * ROW_H), (18, 18, 18))
        dr = ImageDraw.Draw(im)
        for i, r in enumerate(chunk):
            y = i * ROW_H
            name = r.get('frame')
            img = cv2.imread(os.path.join(FR, name)) if name else None
            if img is not None:
                band = img[BAND[0]:BAND[1], :]
                im.paste(Image.fromarray(cv2.cvtColor(band, cv2.COLOR_BGR2RGB)), (LEFT, y + 6))
            dr.text((6, y + 4), f'{k + i + 1}. {r["ep"]} {r["ts"]}',
                    font=f1, fill=(255, 220, 120))
            dr.text((6, y + 26), '库: ' + (r.get('old') or '')[:30], font=f2, fill=(235, 235, 235))
            dr.text((6, y + 48), '帧读: ' + (r.get('frame_text') or '(无)')[:26],
                    font=f2, fill=(150, 255, 150))
            dr.line([(0, y + ROW_H - 1), (LEFT + 960, y + ROW_H - 1)], fill=(80, 80, 80), width=1)
        out = os.path.join(REVIEW, f'q_sheet11_{k // per + 1}.jpg')
        im.save(out, quality=93)
        print('saved', out)


if __name__ == '__main__':
    main()
