# -*- coding: utf-8 -*-
"""q_sheet7.py — 为逐帧扫描(q_fill_resolved.json)的候选生成对照表(帧图 + 旧文本 + 逐帧读数)。
用法: python q_sheet7.py [每张行数=12] [--verdict candidate] [--limit N]
输出: review/q_sheet7_<k>.jpg
"""
import json
import os
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
FR = os.path.join(B, 'docs', 'frames')
FONTS = [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf']
ROW_H = 250


def font(sz):
    for f in FONTS:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def load_map():
    s = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


def main():
    per = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 12
    want = sys.argv[sys.argv.index('--verdict') + 1] if '--verdict' in sys.argv else 'candidate'
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 999
    items = json.load(open(os.path.join(REVIEW, 'q_fill_resolved.json'), encoding='utf-8'))
    if want == 'candidate':
        rows = [r for r in items if r.get('verdict') in ('apply_add', 'review')][:limit]
    else:
        rows = [r for r in items if r.get('verdict') == want][:limit]
    MAP = load_map()
    print(f'{len(rows)} 条 (verdict={want})')
    f1, f2 = font(26), font(22)
    for k in range(0, len(rows), per):
        chunk = rows[k:k + per]
        im = Image.new('RGB', (1560, len(chunk) * ROW_H), (24, 24, 24))
        dr = ImageDraw.Draw(im)
        for i, r in enumerate(chunk):
            y = i * ROW_H
            title = next(t for t in MAP if t.startswith(f"[{r['ep']}]")).split('|')[0]
            f = MAP.get(f"{title}|{r['ts']}")
            img = cv2.imread(os.path.join(FR, f)) if f else None
            if img is not None:
                h = img.shape[0]
                band = img[int(800 * h / 1080):h]
                band = cv2.resize(band, (1000, int(band.shape[0] * 1000 / band.shape[1])),
                                  interpolation=cv2.INTER_CUBIC)
                bh = min(band.shape[0], ROW_H - 4)
                im.paste(Image.fromarray(cv2.cvtColor(band[:bh], cv2.COLOR_BGR2RGB)), (548, y + 2))
            dr.text((8, y + 4), f'{k + i + 1}. {r["ep"]} {r["ts"]} sim={r["best_sim_fill"]:.2f} '
                                f'[{r.get("kind", "?")}]', font=f1, fill=(255, 220, 120))
            dr.text((8, y + 40), (r.get('desc') or '')[:44], font=f2, fill=(160, 200, 255))
            dr.text((8, y + 76), '旧: ' + r['old'][:16], font=f1, fill=(230, 230, 230))
            if len(r['old']) > 16:
                dr.text((8, y + 108), '    ' + r['old'][16:32], font=f2, fill=(200, 200, 200))
            bt = r.get('best_text') or ''
            dr.text((8, y + 142), '帧: ' + bt[:16], font=f1, fill=(150, 255, 150))
            if len(bt) > 16:
                dr.text((8, y + 174), '    ' + bt[16:32], font=f2, fill=(140, 230, 140))
            dr.line([(0, y + ROW_H - 1), (1560, y + ROW_H - 1)], fill=(90, 90, 90), width=1)
        out = os.path.join(REVIEW, f'q_sheet7_{want}_{k // per + 1}.jpg')
        im.save(out, quality=92)
        print('saved', out)


if __name__ == '__main__':
    main()
