# -*- coding: utf-8 -*-
"""按定位结果用 DP 做最优时间戳分配(最小化总位移), 用于精修。

与 retime_from_locate.py 的区别: 那里是"贪心向后找空闲秒", 密集区会把靠后的条目
推得很远(实测最多 +10s); 这里在【保持先后次序 + 避开已占用秒】的约束下,
用动态规划求 Σ|新秒 - 实测秒| 最小的分配, 位移分布更均匀。

用法: python retime_dp.py review/p25_verify_locate.json P25 [--apply] [--offmin 4]
"""
import json
import os
import re
import sys

import cv2

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
FR = os.path.join(B, 'docs', 'frames')
V = os.path.join(B, 'Videos')
MAD_OK = 30.0
PAD = 40          # DP 搜索窗口在主目标区间两侧各留的余量(秒)


def sec_of(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return None if not m else int(m.group(1)) * 60 + int(m.group(2))


def ts_of(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def duration(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            cap = cv2.VideoCapture(os.path.join(V, f))
            r = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            return r


def main():
    loc = json.load(open(sys.argv[1], encoding='utf-8'))['result']
    ep = sys.argv[2]
    apply = '--apply' in sys.argv
    off_min = int(sys.argv[sys.argv.index('--offmin') + 1]) if '--offmin' in sys.argv else 4
    since = int(sys.argv[sys.argv.index('--since') + 1]) if '--since' in sys.argv else 0
    dur = int(duration(ep))

    fm = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
    MAP = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])
    path = [os.path.join(CLEAN, f) for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    data = json.load(open(path, encoding='utf-8'))
    title = os.path.basename(path)[:-5]

    items, keep = [], []
    for e in data:
        cur = sec_of(e['timestamp'])
        fr = MAP.get(f'{title}|{e["timestamp"]}')
        info = loc.get(fr) if fr else None
        ok = bool(info) and info[0][1] <= MAD_OK
        if cur < since:
            keep.append(e)
        elif ok and (abs(info[0][0] - cur) >= off_min or cur > dur):
            items.append({'e': e, 'fr': fr, 'cur': cur, 'tgt': info[0][0], 'mad': info[0][1]})
        else:
            keep.append(e)

    if not items:
        print(f'{ep}: 无需要精修的条目')
        return

    items.sort(key=lambda r: (r['tgt'], r['cur']))
    taken = {sec_of(e['timestamp']) for e in keep}
    taken_name = set(os.listdir(FR)) - {r['fr'] for r in items}
    taken_name |= {v for k, v in MAP.items() if not k.startswith(f'[{ep}]')}

    lo = max(0, min(r['tgt'] for r in items) - PAD)
    hi = min(dur, max(r['tgt'] for r in items) + PAD)
    secs = [s for s in range(lo, hi + 1) if s not in taken]
    n, m = len(items), len(secs)
    INF = float('inf')

    # f[i][j] = 前 i 条放在 secs[0..j] 且第 i 条落在 secs[j] 的最小总代价
    # 代价取位移的平方: 抑制"个别条目被推很远"的离群解
    f = [[INF] * m for _ in range(n)]
    back = [[-1] * m for _ in range(n)]
    for j, s in enumerate(secs):
        f[0][j] = (s - items[0]['tgt']) ** 2
    for i in range(1, n):
        best, arg = INF, -1
        for j in range(m):
            if j > 0 and f[i - 1][j - 1] < best:
                best, arg = f[i - 1][j - 1], j - 1
            if best < INF:
                f[i][j] = best + (secs[j] - items[i]['tgt']) ** 2
                back[i][j] = arg
    end = min(range(m), key=lambda j: f[n - 1][j])
    if f[n - 1][end] == INF:
        print(f'{ep}: DP 无可行解')
        return
    assign = [0] * n
    j = end
    for i in range(n - 1, -1, -1):
        assign[i] = secs[j]
        j = back[i][j]

    plan = []
    for r, s in zip(items, assign):
        nm = f'{ep}_{ts_of(s)}.jpg'
        if nm in taken_name:            # 名字被占用则顺延(少见)
            s2 = s
            while f'{ep}_{ts_of(s2)}.jpg' in taken_name or s2 in taken:
                s2 += 1
            s = s2
            nm = f'{ep}_{ts_of(s)}.jpg'
        taken.add(s)
        taken_name.add(nm)
        plan.append((r, s, nm))
        if apply:
            r['e']['timestamp'] = ts_of(s)
            if nm != r['fr']:
                os.rename(os.path.join(FR, r['fr']), os.path.join(FR, nm))
    if apply:
        json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    deltas = [abs(s - r['tgt']) for r, s, _ in plan]
    lines = [f'{ep} DP 精修: {len(plan)} 条' + ('(已落盘)' if apply else '(预演)')
             + f', 位移 平均{sum(deltas) / len(deltas):.1f}s 最大{max(deltas)}s']
    for r, s, nm in plan:
        lines.append(f"  {r['e']['timestamp'] if not apply else ts_of(s):>7s} -> {ts_of(s):>7s} "
                     f"(实测{ts_of(r['tgt'])}, 位移{s - r['tgt']:+d}s) {r['e'].get('text', '')[:24]:26s} {r['fr']} -> {nm}")
    txt = '\n'.join(lines)
    open(os.path.join(B, 'review', f'retime_dp_{ep}.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
