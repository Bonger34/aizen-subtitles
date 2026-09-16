# -*- coding: utf-8 -*-
"""把带外扫出的 6 条台词入库: 2 条替换掉库中的碎片文本, 3 条新增(含抽帧)。

带外 = 双语字幕块(日文在上/中文在下), 中文那行落在 y≈980-1040, 字幕带内 >245 占比仅
0.005~0.011 < 阈值 0.02, 因此当年整段未被检测到。
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

# (集, 原时间戳, 原文本片段, 新文本)  —— 替换碎片
REPLACE = [('P11', '10m11s', '山十', '打败怪兽时的必杀技超帅'),
           ('P18', '9m26s', '一人', '奥特战士的爸爸哦')]
# (集, 秒, 文本) —— 新增(需抽帧)
ADD = [('P18', 7 * 60 + 58, '这个蓝色表示的就是地球'),
       ('P18', 8 * 60 + 19, '没关系的'),
       ('P18', 8 * 60 + 21, '明天我仍然会继续制作T恤')]


def ts_of(s):
    return f'{s // 60}m{s % 60:02d}s'


def sec_of(t):
    m = re.match(r'(\d+)m(\d+)s', t or '')
    return int(m.group(1)) * 60 + int(m.group(2))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def main():
    apply = '--apply' in sys.argv
    log = []
    # 1) 替换碎片
    for ep, ts, frag, new in REPLACE:
        p = [os.path.join(CLEAN, f) for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
        data = json.load(open(p, encoding='utf-8'))
        hit = 0
        for e in data:
            if e['timestamp'] == ts and (e.get('text') or '').strip() == frag:
                e['text'] = new
                hit += 1
        log.append(f'  替换 {ep} {ts} [{frag}] -> [{new}]  (命中 {hit})')
        if apply and hit:
            json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # 2) 新增条目并抽帧
    for ep, sec, text in ADD:
        p = [os.path.join(CLEAN, f) for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
        data = json.load(open(p, encoding='utf-8'))
        taken = {sec_of(e['timestamp']) for e in data}
        s = sec
        while s in taken or f'{ep}_{ts_of(s)}.jpg' in set(os.listdir(FR)):
            s += 1
        name = f'{ep}_{ts_of(s)}.jpg'
        log.append(f'  新增 {ep} {ts_of(sec)} -> {ts_of(s)}  [{text}]  {name}')
        if apply:
            cap = cv2.VideoCapture(find_video(ep))
            fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
            tgt = int(round(s * fps))
            n = 0
            ok = False
            while n <= tgt:
                if not cap.grab():
                    break
                n += 1
                if n - 1 >= tgt:
                    ok, frame = cap.retrieve()
                    break
            cap.release()
            if ok and frame is not None:
                cv2.imwrite(os.path.join(FR, name),
                            cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA),
                            [cv2.IMWRITE_JPEG_QUALITY, 90])
            else:
                log.append(f'     !! {name} 抽帧失败')
            data.append({'timestamp': ts_of(s), 'similarity': 0.0, 'text': text})
            data.sort(key=lambda e: sec_of(e['timestamp']))
            json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print('\n'.join(log) + ('\n(已落盘)' if apply else '\n(预演)'))


if __name__ == '__main__':
    main()
