# -*- coding: utf-8 -*-
"""q_sheet_v.py — 为帧图验证结果生成对照表: 帧图字幕带 + 旧/时间线新/帧图读数。

用法: python q_sheet_v.py <review|unmatched> <模式> [每张行数]
   模式 support_new : 帧图支持时间线新文本(sim>=0.9)
        unclear     : 两边都不明确
        support_old : 帧图支持旧文本
输出: review/q_sheetv_<模式>_<k>.jpg
"""
import json
import os
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
FR = os.path.join(B, 'Web', 'frames')
FONT_CANDS = [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf']
ROW_H = 250


def get_font(size):
    for f in FONT_CANDS:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                continue
    return ImageFont.load_default()


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else 'review'
    mode = sys.argv[2] if len(sys.argv) > 2 else 'support_new'
    per = int(sys.argv[3]) if len(sys.argv) > 3 else 18
    d = json.load(open(os.path.join(REVIEW, f'q_verify_{kind}.json'), encoding='utf-8'))
    rows = []
    for r in d['items']:
        so, sn = r['sim_frame_old'], r.get('sim_frame_new', 0)
        if mode == 'support_new' and sn >= 0.9 and sn > so:
            rows.append(r)
        elif mode == 'strict' and sn >= 0.98 and so < 0.98:
            # 帧图读数与时间线新文本完全一致、却与旧文本不一致 -> 两个独立来源互证
            rows.append(r)
        elif mode == 'unclear' and so < 0.9 and sn < 0.9:
            rows.append(r)
        elif mode == 'support_old' and so >= 0.9:
            rows.append(r)
    print(f'{kind}/{mode}: {len(rows)} 条')
    font, font_s = get_font(26), get_font(22)
    for k in range(0, len(rows), per):
        chunk = rows[k:k + per]
        canvas = Image.new('RGB', (1560, len(chunk) * ROW_H), (24, 24, 24))
        dr = ImageDraw.Draw(canvas)
        for i, r in enumerate(chunk):
            y = i * ROW_H
            band = None
            if r.get('frame'):
                img = cv2.imread(os.path.join(FR, r['frame']))
                if img is not None:
                    h = img.shape[0]
                    band = img[int(810 * h / 1080):h]
                    band = cv2.resize(band, (1000, int(band.shape[0] * 1000 / band.shape[1])),
                                      interpolation=cv2.INTER_CUBIC)
            if band is not None:
                bh = min(band.shape[0], ROW_H - 4)
                canvas.paste(Image.fromarray(cv2.cvtColor(band[:bh], cv2.COLOR_BGR2RGB)), (548, y + 2))
            dr.text((8, y + 4), f'{k + i + 1}. {r["ep"]} {r["ts"]} [{r.get("kind") or r["verdict0"]}]',
                    font=font, fill=(255, 220, 120))
            dr.text((8, y + 38), f'sim旧={r["sim_frame_old"]:.2f} sim新={r.get("sim_frame_new", 0):.2f} '
                                f'时间线sim={r.get("sim_tl") or 0:.2f}', font=font_s, fill=(160, 200, 255))
            dr.text((8, y + 70), '旧: ' + r['old'][:16], font=font, fill=(230, 230, 230))
            if len(r['old']) > 16:
                dr.text((8, y + 100), '    ' + r['old'][16:32], font=font_s, fill=(200, 200, 200))
            dr.text((8, y + 128), '新: ' + (r.get('new_tl') or '')[:16], font=font, fill=(150, 255, 150))
            if len(r.get('new_tl') or '') > 16:
                dr.text((8, y + 158), '    ' + r['new_tl'][16:32], font=font_s, fill=(140, 230, 140))
            dr.text((8, y + 190), '帧图读: ' + (r.get('frame_text') or '')[:16], font=font_s,
                    fill=(255, 180, 180))
            dr.line([(0, y + ROW_H - 1), (1560, y + ROW_H - 1)], fill=(90, 90, 90), width=1)
        out = os.path.join(REVIEW, f'q_sheetv_{mode}_{k // per + 1}.jpg')
        canvas.save(out, quality=92)
        print('saved', out)


if __name__ == '__main__':
    main()
