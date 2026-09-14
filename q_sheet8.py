# -*- coding: utf-8 -*-
"""q_sheet8.py — 为"帧图重抽失败的疑似正片台词"生成人工对照表。

这 150 条是当前唯一已知开口: ±1.6s / ±3.5s 内都找不到与库文本一致的字幕帧。
自动路径已到极限(实测 9 条"补全候选"全是 Latin 噪声粘连, 如 `...egre`/`...ho`/`...alUe`)。
对照表给出该条目**用户实际会看到的画面**(帧图)+ 上下文台词, 供人工一眼判断。

用法: python q_sheet8.py [--per 15]
输出: review/q_sheet8_<k>.jpg
"""
import json
import os
import re
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
FR = os.path.join(B, 'Web', 'frames')
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


def main():
    per = 15
    if '--per' in sys.argv:
        per = int(sys.argv[sys.argv.index('--per') + 1])
    rows = json.load(open(os.path.join(REVIEW, 'q_suspect_class.json'), encoding='utf-8'))
    M = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                             open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read(),
                             re.S).group(1))
    lib = {}
    for f in sorted(os.listdir(os.path.join(B, 'subtitle_clean'))):
        if not (f.endswith('.json') and re.match(r'^\[P\d+\]', f)):
            continue
        ep = re.search(r'\[(P\d+)\]', f).group(1)
        ent = json.load(open(os.path.join(B, 'subtitle_clean', f), encoding='utf-8'))
        for i, e in enumerate(ent):
            lib[(ep, e.get('timestamp'))] = (ent[i - 1].get('text', '') if i else '',
                                             e.get('text', ''),
                                             ent[i + 1].get('text', '') if i + 1 < len(ent) else '')
    f1, f2 = font(23), font(19)
    print(f'{len(rows)} 条')
    for k in range(0, len(rows), per):
        chunk = rows[k:k + per]
        im = Image.new('RGB', (1560, len(chunk) * ROW_H), (24, 24, 24))
        dr = ImageDraw.Draw(im)
        for i, r in enumerate(chunk):
            y = i * ROW_H
            name = M.get(next((x for x in M if x.endswith('|' + r['ts'])
                               and x.startswith(f"[{r['ep']}]")), ''))
            img = cv2.imread(os.path.join(FR, name)) if name else None
            if img is not None:
                b = cv2.resize(img, (620, 349))
                im.paste(Image.fromarray(cv2.cvtColor(b[:ROW_H - 4], cv2.COLOR_BGR2RGB)),
                         (930, y + 2))
                dr.text((930, y + ROW_H - 20), name or '', font=f2, fill=(150, 150, 150))
            pv, cur, nx = lib.get((r['ep'], r['ts']), ('', r['old'], ''))
            dr.text((8, y + 4), f'{k + i + 1}. {r["ep"]} {r["ts"]}  [{r["guess"]}]',
                    font=f1, fill=(255, 220, 120))
            dr.text((8, y + 36), '上: ' + pv[:26], font=f2, fill=(150, 150, 150))
            dr.text((8, y + 66), '本: ' + cur[:26], font=f1, fill=(235, 235, 235))
            if len(cur) > 26:
                dr.text((8, y + 96), '    ' + cur[26:52], font=f2, fill=(210, 210, 210))
            dr.text((8, y + 128), '下: ' + nx[:26], font=f2, fill=(150, 150, 150))
            dr.text((8, y + 162), '窗口读数: ' + (r['ev'] or '(无)')[:30], font=f2,
                    fill=(150, 255, 150))
            dr.line([(0, y + ROW_H - 1), (1560, y + ROW_H - 1)], fill=(90, 90, 90), width=1)
        out = os.path.join(REVIEW, f'q_sheet8_{k // per + 1}.jpg')
        im.save(out, quality=92)
        print('saved', out)


if __name__ == '__main__':
    main()
