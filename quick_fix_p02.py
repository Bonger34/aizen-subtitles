# -*- coding: utf-8 -*-
"""quick_fix.py — P02 4m48s 冲突修复 + 重建库 4m48s 帧"""
import json
import os
import re

import cv2

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FRAMES = os.path.join(BASE, 'Web', 'frames')
CLEAN = os.path.join(BASE, 'subtitle_clean')
FMAP = os.path.join(BASE, 'Web', 'frames_map.js')
AREA = (100, 895, 1820, 985)


def main():
    # 1. 重命名候选帧 4m48s → 4m50s
    src = os.path.join(FRAMES, 'P02_4m48s.jpg')
    dst = os.path.join(FRAMES, 'P02_4m50s.jpg')
    if os.path.exists(src) and not os.path.exists(dst):
        os.rename(src, dst)
        print('帧重命名 P02_4m48s -> P02_4m50s')

    # 2. 重建库 4m48s 帧: 视频 288s(fidx≈6906) 连续读, 取字幕为「我的品味...」的帧
    video = [os.path.join(BASE, 'Videos', v) for v in os.listdir(os.path.join(BASE, 'Videos'))
             if v.startswith('[P02]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(video)
    fidx = 0
    saved = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if 6890 <= fidx <= 6920:
            crop = frame[AREA[1]:AREA[3], AREA[0]:AREA[2]]
            fp = os.path.join(BASE, 'review', 'probe_frames', f'p02fix_{fidx}.jpg')
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            cv2.imwrite(fp, crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
            if fidx == 6906:
                small = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
                cv2.imwrite(os.path.join(FRAMES, 'P02_4m48s.jpg'), small,
                            [cv2.IMWRITE_JPEG_QUALITY, 90])
                saved = fidx
        fidx += 1
    cap.release()
    print('全帧已写 P02_4m48s.jpg (fidx 6906, 待核对字幕)')

    # 3. 库加 4m50s 好看吧 (若未存在)
    f = [x for x in os.listdir(CLEAN) if x.startswith('[P02]') and x.endswith('.json')][0]
    path = os.path.join(CLEAN, f)
    arr = json.load(open(path, encoding='utf-8'))
    if not any(e['timestamp'] == '4m50s' for e in arr):
        arr.append({'timestamp': '4m50s', 'text': '好看吧', 'similarity': 0.0})
        def tk(e):
            m = re.match(r'(\d+)m(\d+)s', e['timestamp'])
            return int(m.group(1)) * 60 + int(m.group(2)) if m else 0
        arr.sort(key=tk)
        json.dump(arr, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('库已加 4m50s 好看吧')
    # 4. frames_map 键
    srcf = open(FMAP, encoding='utf-8').read()
    key = '"[P02]2 兄弟情|4m50s": "P02_4m50s.jpg"'
    if key not in srcf:
        if srcf.rstrip().endswith('};'):
            srcf = srcf.rstrip()[:-1] + '"[P02]2 兄弟情|4m50s": "P02_4m50s.jpg"' + '};'
        else:
            srcf = srcf.rstrip()[:-1] + ', "[P02]2 兄弟情|4m50s": "P02_4m50s.jpg"' + '};'
        open(FMAP, 'w', encoding='utf-8').write(srcf)
        print('frames_map 已加 4m50s 键')


if __name__ == '__main__':
    main()
