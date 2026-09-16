# -*- coding: utf-8 -*-
"""把确认的新台词候选并入字幕库: 顺序读帧抽取配图 -> 追加条目 -> 重建映射与数据库。

输入 JSON: [{"ep":"P01","sec":123,"text":"..."}...]
  - 若目标秒已被占用, 顺延到最近的空闲秒;
  - 帧存为 {集}_{新时刻}.jpg (960x540 q90, 与现有帧一致);
  - 追加条目 similarity 记 0.0。

用法: python apply_new_lines.py review/new_lines.json [--apply]
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


def ts_of(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def sec_of(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return None if not m else int(m.group(1)) * 60 + int(m.group(2))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def main():
    items = json.load(open(sys.argv[1], encoding='utf-8'))
    apply = '--apply' in sys.argv
    by_ep = {}
    for it in items:
        by_ep.setdefault(it['ep'], []).append(it)

    plan = []
    for ep, its in sorted(by_ep.items()):
        path = [os.path.join(CLEAN, f) for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
        data = json.load(open(path, encoding='utf-8'))
        taken = {sec_of(e['timestamp']) for e in data}
        taken_name = set(os.listdir(FR))
        its.sort(key=lambda x: x['sec'])
        for it in its:
            sec = it['sec']
            while sec in taken or f'{ep}_{ts_of(sec)}.jpg' in taken_name:
                sec += 1
            nm = f'{ep}_{ts_of(sec)}.jpg'
            taken.add(sec)
            taken_name.add(nm)
            plan.append({'ep': ep, 'from': it['sec'], 'sec': sec, 'text': it['text'],
                         'name': nm, 'json': path})

        # 顺序读帧抽图(每集一趟, 不用 cap.set 跳转)
        todo = [p for p in plan if p['ep'] == ep]
        if apply and todo:
            cap = cv2.VideoCapture(find_video(ep))
            fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
            tmap = {int(round(p['sec'] * fps)): p for p in todo}
            targets = sorted(tmap)
            n, ti = 0, 0
            while ti < len(targets):
                if not cap.grab():
                    break
                n += 1                       # 当前帧号 = n-1
                if n - 1 >= targets[ti]:
                    ok, frame = cap.retrieve()
                    p = tmap[targets[ti]]
                    if ok:
                        small = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
                        cv2.imwrite(os.path.join(FR, p['name']), small,
                                    [cv2.IMWRITE_JPEG_QUALITY, 90])
                    else:
                        print(f"  !! {ep} {ts_of(p['sec'])} 抽帧失败")
                    ti += 1
            cap.release()
        if apply:
            for p in todo:
                data.append({'timestamp': ts_of(p['sec']), 'similarity': 0.0, 'text': p['text']})
            data.sort(key=lambda e: sec_of(e['timestamp']))
            json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'新增 {len(plan)} 条' + ('(已落盘)' if apply else '(预演)'))
    for p in plan:
        print(f"  {p['ep']} {ts_of(p['from'])} -> {ts_of(p['sec'])}  {p['text'][:34]:36s} {p['name']}")


if __name__ == '__main__':
    main()
