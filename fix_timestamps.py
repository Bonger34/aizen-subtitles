# -*- coding: utf-8 -*-
"""修正"时间戳超出视频长度"的条目: 按视频实测定位改到真实秒, 并重命名配图帧。

证据来源: locate_all.py 的顺序读帧定位结果(帧名 -> [[秒, MAD], ...])。
规则:
  1. 只处理当前时间戳 > 视频长度的条目(本次 25 条);
  2. 定位可信(MAD <= MAD_MAX)→ 用实测秒; 不可信 → 用同块可靠邻居的偏移做线性插值;
  3. 目标秒被占用时取最近的空闲秒(±8s), 同时保证帧名可用;
  4. 帧文件重命名为 {集}_{新时刻}.jpg(名字被占用则保留原名, 只改时间戳)。

用法:
  python fix_timestamps.py review/p25_tail_locate.json           # 预演
  python fix_timestamps.py review/p25_tail_locate.json --apply   # 落盘
"""
import json
import os
import re
import sys

import cv2

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
FR = os.path.join(B, 'Web', 'frames')
V = os.path.join(B, 'Videos')
MAD_MAX = 20.0
SPAN = 8


def sec_of(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return None if not m else int(m.group(1)) * 60 + int(m.group(2))


def ts_of(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def durations():
    d = {}
    for f in os.listdir(V):
        m = re.match(r'\[(P\d+)\]', f)
        if m and f.lower().endswith('.mp4'):
            cap = cv2.VideoCapture(os.path.join(V, f))
            n, fps = cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            d[m.group(1)] = n / fps
    return d


def main():
    loc = json.load(open(sys.argv[1], encoding='utf-8'))['result']
    apply = '--apply' in sys.argv
    dur = durations()
    fm = open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read()
    MAP = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])

    plan, skipped = [], []
    for fn in sorted(os.listdir(CLEAN)):
        m = re.match(r'\[(P\d+)\]', fn)
        if not m:
            continue
        ep = m.group(1)
        path = os.path.join(CLEAN, fn)
        data = json.load(open(path, encoding='utf-8'))
        todo, offsets = [], []
        for e in data:
            old = sec_of(e.get('timestamp'))
            fr = MAP.get(f'{fn[:-5]}|{e["timestamp"]}')
            if old is None or fr is None:
                continue
            info = loc.get(fr)
            if info and info[0][1] <= MAD_MAX:
                offsets.append((old, old - info[0][0]))     # (原秒, 该帧的时间戳偏移)
            if old > dur[ep]:
                todo.append((old, e, fr, info))
        if not todo:
            continue

        fixed_keys = {id(e) for _, e, _, _ in todo}
        taken_sec = {sec_of(e['timestamp']) for e in data if id(e) not in fixed_keys}
        taken_name = {v for k, v in MAP.items() if k.startswith(f'[{ep}]') and v not in {f for _, _, f, _ in todo}}
        taken_name |= set(os.listdir(FR)) - {f for _, _, f, _ in todo}
        offsets.sort()

        for old, e, fr, info in sorted(todo):
            if info and info[0][1] <= MAD_MAX:
                tgt, src = info[0][0], f'实测(MAD={info[0][1]})'
            else:
                # 用可靠邻居偏移线性插值
                n = len(offsets)
                if n == 0:
                    skipped.append((ep, e['timestamp'], e.get('text', ''), '无可靠邻居, 跳过'))
                    continue
                lo = max((o for o in offsets if o[0] <= old), default=offsets[0], key=lambda x: x[0])
                hi = min((o for o in offsets if o[0] >= old), default=offsets[-1], key=lambda x: x[0])
                if hi[0] == lo[0]:
                    off = lo[1]
                else:
                    r = (old - lo[0]) / (hi[0] - lo[0])
                    off = round(lo[1] + r * (hi[1] - lo[1]))
                tgt, src = old - off, f'插值(偏移+{off}s, MAD={info[0][1] if info else "无"})'

            pick = None
            for d in range(0, SPAN + 1):
                for cand in ([tgt] if d == 0 else [tgt - d, tgt + d]):
                    if cand in taken_sec or cand > dur[ep]:
                        continue
                    nm = f'{ep}_{ts_of(cand)}.jpg'
                    if nm in taken_name:
                        continue
                    pick = (cand, nm)
                    break
                if pick:
                    break
            if not pick:
                skipped.append((ep, e['timestamp'], e.get('text', ''), '找不到空闲秒'))
                continue
            cand, nm = pick
            taken_sec.add(cand)
            taken_name.add(nm)
            plan.append((ep, e['timestamp'], ts_of(cand), e.get('text', ''), fr, nm, src,
                         cand == tgt))
            if apply:
                e['timestamp'] = ts_of(cand)
                if nm != fr:
                    os.rename(os.path.join(FR, fr), os.path.join(FR, nm))
        if apply:
            json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    lines = [f'时间戳修正: 改动 {len(plan)} 条, 跳过 {len(skipped)} 条' + ('(已落盘)' if apply else '(预演)')]
    for ep, old, new, text, fr, nm, src, exact in plan:
        mark = '' if exact else ' *避让冲突'
        lines.append(f'  {ep} {old:>7s} -> {new:>7s}{mark}  {text[:24]:26s} {fr} -> {nm}  [{src}]')
    for ep, old, text, why in skipped:
        lines.append(f'  !! {ep} {old:>7s} {text[:24]:26s} 跳过: {why}')
    txt = '\n'.join(lines)
    open(os.path.join(B, 'review', 'retime_plan.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
