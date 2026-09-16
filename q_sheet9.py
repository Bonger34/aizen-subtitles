# -*- coding: utf-8 -*-
"""q_sheet9.py — 为"既没有匹配帧、自身时间戳也没被证实"的残留条目生成人工对照表。

与 q_sheet8 的区别: q_sheet8 只看帧图; q_sheet9 同时给出
  * 用户实际会看到的帧图(画面)
  * 上一条 / 本条 / 下一条库文本(上下文, 判断本句是否通顺)
  * 该时间戳附近的实际画面读数(机器读到的是什么)
用法: python q_sheet9.py [--per 15]
输出: review/q_sheet9_<k>.jpg
"""
import json
import os
import re
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


def main():
    per = 15
    if '--per' in sys.argv:
        per = int(sys.argv[sys.argv.index('--per') + 1])
    src = 'q_review9.json'
    if '--src' in sys.argv:
        src = sys.argv[sys.argv.index('--src') + 1]
    rows = json.load(open(os.path.join(REVIEW, src), encoding='utf-8'))
    M = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                             open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read(),
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
    f1, f2 = font(22), font(19)
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
            pv, cur, nx = lib.get((r['ep'], r['ts']), ('', r['old'], ''))
            dr.text((8, y + 4), f'{k + i + 1}. {r["ep"]} {r["ts"]}', font=f1, fill=(255, 220, 120))
            dr.text((8, y + 34), '上: ' + pv[:27], font=f2, fill=(150, 150, 150))
            dr.text((8, y + 64), '本: ' + cur[:27], font=f1, fill=(240, 240, 240))
            if len(cur) > 27:
                dr.text((8, y + 92), '    ' + cur[27:54], font=f2, fill=(215, 215, 215))
            dr.text((8, y + 124), '下: ' + nx[:27], font=f2, fill=(150, 150, 150))
            dr.text((8, y + 156), '机器读到: ' + (r.get('read') or '(无)')[:26], font=f2,
                    fill=(150, 255, 150))
            dr.line([(0, y + ROW_H - 1), (1560, y + ROW_H - 1)], fill=(90, 90, 90), width=1)
        out = os.path.join(REVIEW, f'q_sheet9_{k // per + 1}.jpg')
        im.save(out, quality=90)
        print('saved', out)


if __name__ == '__main__':
    main()
