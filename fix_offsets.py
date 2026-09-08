# -*- coding: utf-8 -*-
"""
fix_offsets.py — 把偏移过大的补录条目归位到真实秒(±3s 内)
- 对每条: 目标秒=扫描帧秒, 若库占用则找 ±1..±3 中库无条目的秒
- 顺序读帧重新提取该秒全帧(覆盖可能的孤儿帧)
- 删除旧偏移条目, 插入归位条目, 重建 frames_map
"""
import json
import os
import re
import sys

import cv2

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO_DIR = os.path.join(BASE, 'Videos')
FRAMES = os.path.join(BASE, 'Web', 'frames')
CLEAN = os.path.join(BASE, 'subtitle_clean')
FMAP = os.path.join(BASE, 'Web', 'frames_map.js')
REVIEW = os.path.join(BASE, 'review')

# (集, 原扫描秒, 文本, 当前库中的秒)
FIX = [
    ('P04', '0m09s', '秘密比如什么秘密啊', '0m15s'),
    ('P04', '0m24s', '那你来说说看啊', '0m29s'),
    ('P10', '9m58s', '好的', '10m09s'),
    ('P11', '7m19s', '爱染', '7m31s'),
    ('P11', '7m23s', '让市民入危险之中', '7m32s'),
    ('P20', '24m16s', '我们互相仇视对方', '24m30s'),
    ('P20', '24m17s', '根本不能解决问题', '24m31s'),
    ('P20', '24m23s', '那就让我来告诉你们', '24m32s'),
    ('P22', '4m50s', '你回来了', '5m00s'),
    ('P22', '24m08s', '下集也要收看哦', '24m21s'),
    ('P25', '23m26s', '你这次一定要回来啊', '24m27s'),
    ('P25', '23m32s', '好咧', '24m28s'),
    ('P25', '23m33s', '开工干活吧', '24m29s'),
    ('P25', '23m36s', '那我也走', '24m33s'),
    ('P25', '23m37s', '那我也走了', '24m34s'),
    ('P25', '23m52s', '就到此结束了', '24m42s'),
]


def ts_str(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def ts_sec(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2))


def main():
    by_ep = {}
    for ep, t0, tx, t1 in FIX:
        by_ep.setdefault(ep, []).append((t0, tx, t1))
    fmap_src = open(FMAP, encoding='utf-8').read()
    fmap = json.loads(re.search(r'=\s*(\S.*)\s*;', fmap_src, re.S).group(1))

    for ep, items in by_ep.items():
        f = [x for x in os.listdir(CLEAN) if x.startswith(f'[{ep}]') and x.endswith('.json')][0]
        path = os.path.join(CLEAN, f)
        arr = json.load(open(path, encoding='utf-8'))
        title = f[:-5]
        # 1. 删除旧偏移条目
        old_ts = {t1 for _, _, t1 in items}
        arr2 = [e for e in arr if not (e['timestamp'] in old_ts and
                                       any(e['text'] == tx for _, tx, _ in items))]
        removed = len(arr) - len(arr2)
        lib_ts = {e['timestamp'] for e in arr2}
        # 2. 分配目标秒
        plan = {}
        for t0, tx, t1 in items:
            base = ts_sec(t0)
            target = None
            for delta in [0, 1, -1, 2, -2, 3, -3]:
                cand = base + delta
                if cand >= 0 and ts_str(cand) not in lib_ts:
                    target = cand
                    break
            if target is None:
                print(f'  !! {ep} {tx} 无可用秒(±3)')
                continue
            lib_ts.add(ts_str(target))
            plan[target] = tx
        if not plan:
            continue
        # 3. 顺序读帧提取
        cont = json.load(open(os.path.join(REVIEW, f'cont_{ep}.json'), encoding='utf-8'))
        fps = cont['fps']
        want = {int(round(s * fps)): (s, tx) for s, tx in plan.items()}
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
        cap = cv2.VideoCapture(video)
        fidx = 0
        got = {}
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if fidx in want:
                sec, tx = want[fidx]
                fname = f'{ep}_{ts_str(sec)}.jpg'
                small = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
                cv2.imwrite(os.path.join(FRAMES, fname), small, [cv2.IMWRITE_JPEG_QUALITY, 90])
                got[sec] = (fname, tx)
            fidx += 1
        cap.release()
        for sec, (fname, tx) in got.items():
            arr2.append({'timestamp': ts_str(sec), 'text': tx, 'similarity': 0.0})
            fmap[f'{title}|{ts_str(sec)}'] = fname
            print(f'  {ep} {tx} -> {ts_str(sec)} ({fname})')
        arr2.sort(key=lambda e: ts_sec(e['timestamp']))
        json.dump(arr2, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{ep}: 删旧 {removed}, 归位 {len(got)}, 库 {len(arr2)}')

    # 4. 重建映射(清理孤儿键)
    new = {}
    for fn in sorted(os.listdir(CLEAN)):
        if not fn.endswith('.json'):
            continue
        title = fn[:-5]
        ep2 = fn[1:4]
        data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
        for e in data:
            key = f'{title}|{e["timestamp"]}'
            fname = fmap.get(key)
            if fname and os.path.exists(os.path.join(FRAMES, fname)):
                new[key] = fname
            elif os.path.exists(os.path.join(FRAMES, f'{ep2}_{e["timestamp"]}.jpg')):
                new[key] = f'{ep2}_{e["timestamp"]}.jpg'
            else:
                print('缺帧', key)
    open(FMAP, 'w', encoding='utf-8').write('window.FRAMES_MAP = ' + json.dumps(new, ensure_ascii=False) + ';')
    print('映射键数', len(new))


if __name__ == '__main__':
    main()
