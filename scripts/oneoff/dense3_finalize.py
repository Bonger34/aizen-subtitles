# -*- coding: utf-8 -*-
"""最终策展: 排除片尾段(>=23m20s, 该段是演职员表/歌词/图鉴)后的待入库台词清单。

并执行入库: 抽帧 + 追加条目。用法: python dense3_finalize.py [--apply]
"""
import json
import os
import re
import sys

import cv2

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle_clean')
FR = os.path.join(B, 'docs', 'frames')
TAIL = 23 * 60 + 20          # 片尾段起点


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
    cands = json.load(open(os.path.join(B, 'review', 'dense3_final2.json'), encoding='utf-8'))
    # P25 的片尾(含演职员表)从 ~21m 就开始, 单独收紧
    keep = [c for c in cands
            if c['sec'] < (21 * 60 if c['ep'] == 'P25' else TAIL)]
    print(f'策展 {len(cands)} -> 排除片尾段 {len(cands) - len(keep)} -> 待入库 {len(keep)}')
    if not apply:
        import collections
        print('每集:', dict(sorted(collections.Counter(c['ep'] for c in keep).items())))
        for c in sorted(keep, key=lambda x: (x['ep'], x['sec'])):
            print(f"   {c['ep']} {c['t']:>7s}  [{c['text']}]")
        json.dump(keep, open(os.path.join(B, 'review', 'dense3_add.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        return
    lib, files = {}, set(os.listdir(FR))
    for fn in sorted(os.listdir(CLEAN)):
        if fn.endswith('.json'):
            lib[fn[:-5]] = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
    done = 0
    caps = {}
    for c in sorted(keep, key=lambda x: (x['ep'], x['sec'])):
        ep = c['ep']
        title = [k for k in lib if k.startswith(f'[{ep}]')][0]
        data = lib[title]
        want = cn(c['text'])
        if any(cn(e.get('text')) == want and abs(sec_of(e['timestamp']) - c['sec']) <= 8 for e in data):
            continue
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
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((c['sec'] + c.get('delta', 0.0)) * fps)))
        ok, fr = cap.read()
        if ok:
            cv2.imwrite(os.path.join(FR, name),
                        cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])
            files.add(name)
        data.append({'timestamp': ts_of(s), 'similarity': 0.0, 'text': c['text']})
        data.sort(key=lambda e: sec_of(e['timestamp']))
        json.dump(data, open(os.path.join(CLEAN, title + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        done += 1
    for cap in caps.values():
        cap.release()
    print(f'已入库 {done} 条')


if __name__ == '__main__':
    main()
