# -*- coding: utf-8 -*-
"""最后一轮收敛: 从 369 条复核通过里剔除片尾段与"已有条目的片段", 入库剩余真台词。"""
import json
import os
import re
import sys

import cv2

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle_clean')
FR = os.path.join(B, 'docs', 'frames')
TAIL = 22 * 60 + 30      # 片尾/图鉴段起点(本轮统一排除)


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def ts_of(s):
    return f'{int(s) // 60}m{int(s) % 60:02d}s'


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def main():
    apply = '--apply' in sys.argv
    d = json.load(open(os.path.join(B, 'review', 'dense4_report.txt'), encoding='utf-8')) \
        if False else None
    # 从报告里解析通过项
    txt = open(os.path.join(B, 'review', 'dense4_report.txt'), encoding='utf-8').read()
    rows = re.findall(r'^  (P\d+) +(\d+m\d+s) +\[(.+?)\] +画面=\[(.*?)\]$', txt, re.M)
    print(f'报告解析: {len(rows)} 条通过')
    lib, files = {}, set(os.listdir(FR))
    for fn in sorted(os.listdir(CLEAN)):
        if fn.endswith('.json'):
            lib[fn[:-5]] = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
    keep, drop = [], {}
    import collections
    # 跨集重复(片头片尾歌词碎片每集都会出现) -> 排除
    rep = collections.Counter()
    for ep, ts, text, ocr in rows:
        rep[cn(text)] += 1
    for ep, ts, text, ocr in rows:
        sec = sec_of(ts)
        t = cn(text)
        if sec >= (21 * 60 if ep == 'P25' else TAIL):
            drop['片尾/图鉴段'] = drop.get('片尾/图鉴段', 0) + 1
            continue
        if rep[t] >= 3:
            drop['跨集重复(歌词碎片)'] = drop.get('跨集重复(歌词碎片)', 0) + 1
            continue
        title = [k for k in lib if k.startswith(f'[{ep}]')][0]
        near = [cn(e.get('text')) for e in lib[title] if abs(sec_of(e['timestamp']) - sec) <= 8]
        if any(t in lt or lt in t for lt in near):
            drop['已有条目的片段'] = drop.get('已有条目的片段', 0) + 1
            continue
        keep.append({'ep': ep, 't': ts, 'sec': sec, 'text': text, 'ocr': ocr})
    print('剔除:', drop, ' 最终入库:', len(keep))
    for c in sorted(keep, key=lambda x: (x['ep'], x['sec'])):
        print(f"   {c['ep']} {c['t']:>7s}  [{c['text']}]  画面=[{c['ocr']}]")
    if not apply:
        return
    caps = {}
    for c in sorted(keep, key=lambda x: (x['ep'], x['sec'])):
        ep = c['ep']
        title = [k for k in lib if k.startswith(f'[{ep}]')][0]
        data = lib[title]
        taken = {sec_of(e['timestamp']) for e in data}
        s = c['sec']
        name = f'{ep}_{ts_of(s)}.jpg'
        while s in taken or name in files:
            s += 1
            name = f'{ep}_{ts_of(s)}.jpg'
        if ep not in caps:
            caps[ep] = cv2.VideoCapture(find_video(ep))
        cap = caps[ep]
        fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(c['sec'] * fps)))
        r, fr = cap.read()
        if r:
            cv2.imwrite(os.path.join(FR, name),
                        cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])
            files.add(name)
        data.append({'timestamp': ts_of(s), 'similarity': 0.0, 'text': c['text']})
        data.sort(key=lambda e: sec_of(e['timestamp']))
        json.dump(data, open(os.path.join(CLEAN, title + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    for cap in caps.values():
        cap.release()
    print(f'已入库 {len(keep)} 条')


if __name__ == '__main__':
    main()
