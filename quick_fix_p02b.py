# -*- coding: utf-8 -*-
"""quick_fix_p02b.py — P02 4m47/4m48/4m49 精修:
- 4m47s 好看吧(fidx 6871), 4m49s 我的品味... (fidx 6919), 库时间戳 4m48s -> 4m49s
- 从视频连续读提取两个全帧, 修正库与 frames_map
"""
import json
import os
import re

import cv2

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FRAMES = os.path.join(BASE, 'Web', 'frames')
CLEAN = os.path.join(BASE, 'subtitle_clean')
FMAP = os.path.join(BASE, 'Web', 'frames_map.js')


def main():
    video = [os.path.join(BASE, 'Videos', v) for v in os.listdir(os.path.join(BASE, 'Videos'))
             if v.startswith('[P02]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(video)
    want = {6871: 'P02_4m47s.jpg', 6919: 'P02_4m49s.jpg'}
    fidx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if fidx in want:
            small = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
            cv2.imwrite(os.path.join(FRAMES, want[fidx]), small, [cv2.IMWRITE_JPEG_QUALITY, 90])
        fidx += 1
    cap.release()
    print('帧已提取 4m47s/4m49s')

    # 清理无效帧
    for f in ['P02_4m48s.jpg', 'P02_4m50s.jpg', 'P02_4m46s.jpg']:
        p = os.path.join(FRAMES, f)
        if os.path.exists(p):
            os.remove(p)
            print('删除', f)

    # 库条目修正
    f = [x for x in os.listdir(CLEAN) if x.startswith('[P02]') and x.endswith('.json')][0]
    path = os.path.join(CLEAN, f)
    arr = json.load(open(path, encoding='utf-8'))
    arr2 = []
    for e in arr:
        if e['timestamp'] == '4m48s' and e['text'] == '我的品味连我自己都感到害怕':
            arr2.append({'timestamp': '4m49s', 'text': e['text'], 'similarity': e.get('similarity', 0.0)})
        else:
            arr2.append(e)
    if not any(e['timestamp'] == '4m47s' for e in arr2):
        arr2.append({'timestamp': '4m47s', 'text': '好看吧', 'similarity': 0.0})
    def tk(e):
        m = re.match(r'(\d+)m(\d+)s', e['timestamp'])
        return int(m.group(1)) * 60 + int(m.group(2)) if m else 0
    arr2.sort(key=tk)
    json.dump(arr2, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('库修正完成')

    # frames_map 键
    s = open(FMAP, encoding='utf-8').read()
    s = s.replace('"[P02]2 兄弟情|4m48s": "P02_4m48s.jpg"', '"[P02]2 兄弟情|4m49s": "P02_4m49s.jpg"')
    s = s.replace('"[P02]2 兄弟情|4m50s": "P02_4m50s.jpg"', '"[P02]2 兄弟情|4m47s": "P02_4m47s.jpg"')
    open(FMAP, 'w', encoding='utf-8').write(s)
    print('frames_map 修正完成')


if __name__ == '__main__':
    main()
