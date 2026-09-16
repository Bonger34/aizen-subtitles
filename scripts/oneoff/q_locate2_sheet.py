# -*- coding: utf-8 -*-
"""q_locate2_sheet.py — 把 q_locate2 定位到的**原片帧**做成对照表, 供人工看图判定。

与 q_sheet7 的区别: 这里贴的是 1080p 原片在被定位帧处的字幕带(而不是 960x540 帧图),
所以能看到真正要核对的画面。

用法: python q_locate2_sheet.py [--rel add,diff,del] [--scope in|all] [--per 10]
输出: review/q_locate2_sheet_<rel>_<k>.jpg
"""
import json
import os
import re
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
VIDEO_DIR = os.path.join(B, 'Videos')
FONTS = [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf']
ROW_H = 252
CROP_TOP = 780


def font(sz):
    for f in FONTS:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def load_rows():
    rows = []
    for f in sorted(os.listdir(REVIEW)):
        if re.fullmatch(r'q_locate2_P\d+\.json', f):
            rows.extend(json.load(open(os.path.join(REVIEW, f), encoding='utf-8')))
    stat = os.path.join(REVIEW, 'q_locate2_stat.json')
    if os.path.exists(stat):
        scope = {(r['ep'], r['ts']): r.get('scope', 'in')
                 for r in json.load(open(stat, encoding='utf-8'))['rows']}
        for r in rows:
            r['scope'] = scope.get((r['ep'], r['ts']), 'in')
    else:
        for r in rows:
            r['scope'] = 'in'
    return rows


def grab_bands(ep, fnos):
    """顺序读一遍该集, 取回 fnos 处的字幕带裁剪(1080p)。返回 {fno: bgr}。"""
    vid = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    want = sorted(set(fnos))
    out, n, i = {}, 0, 0
    while i < len(want):
        if not cap.grab():
            break
        if n == want[i]:
            ok, fr = cap.retrieve()
            if ok:
                out[n] = fr[CROP_TOP:1080].copy()
            i += 1
        n += 1
    cap.release()
    return out


def main():
    args = sys.argv[1:]
    rels = 'add,diff,del'.split(',')
    scope, per = 'in', 10
    if '--rel' in args:
        rels = args[args.index('--rel') + 1].split(',')
    if '--scope' in args:
        scope = args[args.index('--scope') + 1]
    if '--per' in args:
        per = int(args[args.index('--per') + 1])

    rows = [r for r in load_rows()
            if r['rel'] in rels and r['fno'] is not None
            and (scope == 'all' or r.get('scope') == 'in')]
    rows.sort(key=lambda r: (r['ep'], r['fno']))
    print(f'{len(rows)} 条 (rel={rels}, scope={scope})')
    if not rows:
        return

    bands = {}
    for ep in sorted({r['ep'] for r in rows}):
        sub = [r for r in rows if r['ep'] == ep]
        bands.update({(ep, k): v for k, v in grab_bands(ep, [r['fno'] for r in sub]).items()})
        print(f'  {ep}: {len(sub)} 帧已取', flush=True)

    f1, f2 = font(25), font(21)
    tag = f'{rels[0]}_{scope}'
    k = 0
    for k in range(0, len(rows), per):
        chunk = rows[k:k + per]
        im = Image.new('RGB', (1560, len(chunk) * ROW_H), (24, 24, 24))
        dr = ImageDraw.Draw(im)
        for i, r in enumerate(chunk):
            y = i * ROW_H
            b = bands.get((r['ep'], r['fno']))
            if b is not None:
                b = cv2.resize(b, (1000, int(b.shape[0] * 1000 / b.shape[1])),
                               interpolation=cv2.INTER_AREA)
                im.paste(Image.fromarray(cv2.cvtColor(b, cv2.COLOR_BGR2RGB)), (548, y + 2))
            dr.text((8, y + 4), f'{k + i + 1}. {r["ep"]} {r["ts"]} iou={r["iou"]:.2f} '
                                f'off={r["offset"]} sim={r["sim"]:.2f} [{r["rel"]}]',
                    font=f1, fill=(255, 220, 120))
            dr.text((8, y + 38), f'帧序号 {r["fno"]}  {r.get("scope", "")}', font=f2,
                    fill=(160, 200, 255))
            dr.text((8, y + 70), '旧: ' + r['old'][:14], font=f1, fill=(230, 230, 230))
            if len(r['old']) > 14:
                dr.text((8, y + 102), '    ' + r['old'][14:28], font=f2, fill=(200, 200, 200))
            nt = r['text'] or '(未读出)'
            dr.text((8, y + 138), '新: ' + nt[:14], font=f1, fill=(150, 255, 150))
            if len(nt) > 14:
                dr.text((8, y + 170), '    ' + nt[14:28], font=f2, fill=(140, 230, 140))
            dr.line([(0, y + ROW_H - 1), (1560, y + ROW_H - 1)], fill=(90, 90, 90), width=1)
        out = os.path.join(REVIEW, f'q_locate2_sheet_{tag}_{k // per + 1}.jpg')
        im.save(out, quality=92)
        print('saved', out)


if __name__ == '__main__':
    main()
