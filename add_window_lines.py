# -*- coding: utf-8 -*-
"""补入窗口扫描发现的 3 条漏句(已目视 + 全库检索确认)。

只写入 subtitle_clean 与帧文件; frames_map 交给 rebuild_map.py 重建。
"""
import json
import os
import sys

import cv2

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle_clean')
FR = os.path.join(B, 'Web', 'frames')

ADD = [('P22', 16 * 60 + 6, '休想得逞'), ('P22', 16 * 60 + 50, '勇海 我们上'),
       ('P24', 17 * 60 + 14, '明白发射牵引光束')]


def ts_of(s):
    return f'{s // 60}m{s % 60:02d}s'


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def main():
    apply = '--apply' in sys.argv
    files = set(os.listdir(FR))
    log = []
    for ep, sec, text in ADD:
        p = [os.path.join(CLEAN, f) for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
        data = json.load(open(p, encoding='utf-8'))
        taken = {sec_of(e['timestamp']) for e in data}
        s = sec
        while s in taken or f'{ep}_{ts_of(s)}.jpg' in files:
            s += 1
        name = f'{ep}_{ts_of(s)}.jpg'
        log.append(f'  {ep} {ts_of(sec)} -> {ts_of(s)}  [{text}]  {name}')
        if not apply:
            continue
        cap = cv2.VideoCapture(find_video(ep))
        fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(s * fps)))
        ok, fr = cap.read()
        cap.release()
        if not ok:
            log.append(f'     !! {name} 抽帧失败')
        else:
            cv2.imwrite(os.path.join(FR, name),
                        cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])
            files.add(name)
        data.append({'timestamp': ts_of(s), 'similarity': 0.0, 'text': text})
        data.sort(key=lambda e: sec_of(e['timestamp']))
        json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n'.join(log) + ('\n(已落盘)' if apply else '\n(预演)'))


if __name__ == '__main__':
    main()
