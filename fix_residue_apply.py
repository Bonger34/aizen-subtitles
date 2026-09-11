# -*- coding: utf-8 -*-
"""收尾: 修复 9 条残留中的 7 条(改文本 + 抽对应秒的帧), 剩 2 条为纯垃圾条目不处理。

每条: (集, 时间戳, 原文本, 取帧偏移秒, 新文本)
"""
import json
import os
import re
import sys

import cv2

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle_clean')
FR = os.path.join(B, 'Web', 'frames')
FMAP = os.path.join(B, 'Web', 'frames_map.js')

FIX = [('P06', '18m52s', '哥哥', 0.5, '哥哥'),
       ('P13', '14m19s', '重', 0.0, '这是'),
       ('P13', '14m29s', '口', 0.5, '应该是勇海的吧'),
       ('P17', '18m38s', '金', 0.25, '被关起来了'),
       ('P19', '9m41s', '》名', 0.0, '关闭系统'),
       ('P20', '24m08s', '释放山志的招振油', 0.0, '释放出来的超振动波'),
       ('P23', '9m28s', '仍尚不明确', 0.0, '难道说')]


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def main():
    apply = '--apply' in sys.argv
    MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;', open(FMAP, encoding='utf-8').read(), re.S).group(1))
    files = set(os.listdir(FR))
    log = []
    for ep, ts, old, off, new in FIX:
        name = f'{ep}_{ts}.jpg'
        if name in files:
            name = f'{ep}_{ts}_fix.jpg'
        log.append(f'  {ep} {ts}  [{old}] -> [{new}]  帧 {off:+.2f}s -> {name}')
        if not apply:
            continue
        cap = cv2.VideoCapture(find_video(ep))
        fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((sec_of(ts) + off) * fps)))
        ok, fr = cap.read()
        cap.release()
        if ok:
            cv2.imwrite(os.path.join(FR, name),
                        cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])
            files.add(name)
        else:
            log.append(f'     !! {name} 抽帧失败')
        for k in [k for k in MAP if k.startswith(f'[{ep}]') and k.endswith('|' + ts)]:
            MAP[k] = name
        p = [os.path.join(CLEAN, f) for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
        data = json.load(open(p, encoding='utf-8'))
        for e in data:
            if e['timestamp'] == ts and (e.get('text') or '').strip() == old:
                e['text'] = new
        json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if apply:
        open(FMAP, 'w', encoding='utf-8').write('window.FRAMES_MAP = ' +
                                                json.dumps(MAP, ensure_ascii=False) + ';')
    print('\n'.join(log) + ('\n(已落盘)' if apply else '\n(预演)'))


if __name__ == '__main__':
    main()
