# -*- coding: utf-8 -*-
"""q_sheet.py — 为待人工核对的条目生成帧图对照表(帧图字幕带 + 旧/新文本 + 序号)。

用 PIL 画中文标注(OpenCV 不支持中文)。每张表最多 N 行, 便于逐条核对插入的数字/字母
到底是字幕内容还是画面 UI(帧计数器、倒计时特效、装饰线)。
用法: python q_sheet.py [verdict=apply_add] [每张行数=22] [起始序号=0]
输出: review/q_sheet_<verdict>_<k>.jpg
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
FR = os.path.join(B, 'docs', 'frames')
FONT_CANDS = [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf',
              r'C:\Windows\Fonts\simsun.ttc']
ROW_H = 210


def get_font(size):
    for f in FONT_CANDS:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                continue
    return ImageFont.load_default()


def main():
    verdict = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'apply_add'
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 22
    d = json.load(open(os.path.join(REVIEW, 'q_align_tl.json'), encoding='utf-8'))
    s = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
    MAP = json.loads(s[s.index('{'):s.rindex('}') + 1])
    rows = []
    for ep in sorted(d):
        for r in d[ep]['items']:
            if r.get('verdict') == verdict:
                rows.append((ep, r))
    print(f'{verdict}: {len(rows)} 条, 每张 {per} 行')
    font = get_font(26)
    font_s = get_font(22)
    for k in range(0, len(rows), per):
        chunk = rows[k:k + per]
        canvas = Image.new('RGB', (1560, len(chunk) * ROW_H), (24, 24, 24))
        dr = ImageDraw.Draw(canvas)
        for i, (ep, r) in enumerate(chunk):
            y = i * ROW_H
            title = next(t for t in MAP if t.startswith(f'[{ep}]')).split('|')[0]
            f = MAP.get(f'{title}|{r["ts"]}')
            band = None
            if f:
                img = cv2.imread(os.path.join(FR, f))
                if img is not None:
                    h = img.shape[0]
                    band = img[int(820 * h / 1080):h]
                    band = cv2.resize(band, (1000, int(band.shape[0] * 1000 / band.shape[1])),
                                      interpolation=cv2.INTER_CUBIC)
            if band is not None:
                bh = min(band.shape[0], ROW_H - 4)
                canvas.paste(Image.fromarray(cv2.cvtColor(band[:bh], cv2.COLOR_BGR2RGB)), (556, y + 2))
            dr.text((8, y + 6), f'{k + i + 1}. {ep} {r["ts"]}', font=font, fill=(255, 220, 120))
            dr.text((8, y + 40), f'sim={r["best_sim"]:.2f} sup={r.get("support")} '
                                f'{r.get("desc", "")[:34]}', font=font_s, fill=(160, 200, 255))
            dr.text((8, y + 74), '旧:' + r['old'][:15], font=font, fill=(230, 230, 230))
            dr.text((8, y + 108), '新:' + r['new'][:15], font=font, fill=(150, 255, 150))
            if len(r['old']) > 15:
                dr.text((8, y + 142), '   ' + r['old'][15:30], font=font_s, fill=(200, 200, 200))
            if len(r['new']) > 15:
                dr.text((8, y + 168), '   ' + r['new'][15:30], font=font_s, fill=(140, 230, 140))
            dr.line([(0, y + ROW_H - 1), (1560, y + ROW_H - 1)], fill=(90, 90, 90), width=1)
        out = os.path.join(REVIEW, f'q_sheet_{verdict}_{k // per + 1}.jpg')
        canvas.save(out, quality=92)
        print('saved', out)


if __name__ == '__main__':
    main()
