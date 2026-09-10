# -*- coding: utf-8 -*-
"""按视频定位结果重排某集的时间戳。

思路(针对 P25 片尾整段错位):
  1. 每条条目的配图帧都在视频里定位过 -> 得到一个"内容真实秒";
  2. 按内容真实秒排序(而不是按当前时间戳, 因为当前顺序本身已被打乱);
  3. 依序装箱: 每条取 >= 内容真实秒 的最小空闲秒(保持先后次序, 最小位移);
  4. 帧文件同步重命名为 {集}_{新时刻}.jpg。

用法: python retime_from_locate.py review/p25_all_locate.json P25 [--apply]
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
PEAK_OK = 0.75      # (保留) 峰值比判据
MAD_OK = 30.0       # 定位可用的 MAD 上限
OFF_MIN = 4         # 偏移达到该秒数才判定为真错位(测量噪声约 ±1s)


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


def reliable(best, second):
    """定位是否可用: 最佳匹配的 MAD 不超过上限。

    注: 片尾滚动职员表使 MAD 曲线平缓, "最佳明显优于次佳"在此不适用,
        改用 MAD 上限 + 偏移阈值(|偏移| >= OFF_MIN 才判定为真错位)。
    """
    return best[1] <= MAD_OK


def main():
    loc = json.load(open(sys.argv[1], encoding='utf-8'))['result']
    ep = sys.argv[2]
    apply = '--apply' in sys.argv
    dur = duration(ep)

    fm = open(os.path.join(B, 'Web', 'frames_map.js'), encoding='utf-8').read()
    MAP = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])
    path = [os.path.join(CLEAN, f) for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
    data = json.load(open(path, encoding='utf-8'))
    title = os.path.basename(path)[:-5]

    rows, nopeak = [], []
    for e in data:
        cur = sec_of(e.get('timestamp'))
        fr = MAP.get(f'{title}|{e["timestamp"]}')
        info = loc.get(fr) if fr else None
        if not info:
            nopeak.append((e, fr, '无定位'))
            continue
        best = info[0]
        second = info[1] if len(info) > 1 else None
        if not reliable(best, second):
            nopeak.append((e, fr, f'峰值不明确(MAD={best[1]})'))
            continue
        rows.append({'e': e, 'fr': fr, 'cur': cur, 'true': best[0], 'mad': best[1]})

    # 峰值不明确但时间戳已越界者: 用可靠邻居的偏移线性插值补出内容时间
    rel = sorted((r['cur'], r['cur'] - r['true']) for r in rows)
    filled = []
    if rel:
        for e, fr, why in list(nopeak):
            cur = sec_of(e.get('timestamp'))
            if cur <= dur:
                continue
            lo = max((x for x in rel if x[0] <= cur), default=rel[0], key=lambda x: x[0])
            hi = min((x for x in rel if x[0] >= cur), default=rel[-1], key=lambda x: x[0])
            off = lo[1] if hi[0] == lo[0] else round(lo[1] + (cur - lo[0]) / (hi[0] - lo[0]) * (hi[1] - lo[1]))
            rows.append({'e': e, 'fr': fr, 'cur': cur, 'true': cur - off, 'mad': None})
            nopeak.remove((e, fr, why))
            filled.append((e, cur, cur - off, off))

    # 需要改动的: 与实测内容时间相差 >= OFF_MIN 秒(测量噪声约 ±1s),
    # 或者当前时间戳已超出视频长度(必定错误)
    todo, minor = [], []
    for r in rows:
        d = r['true'] - r['cur']
        if abs(d) >= OFF_MIN or r['cur'] > dur:
            todo.append(r)
        elif d != 0:
            minor.append((r, d))
    fixed_ids = {id(r['e']) for r in todo}
    taken = {sec_of(e['timestamp']) for e in data if id(e) not in fixed_ids}
    taken_name = {v for k, v in MAP.items() if not k.startswith(f'[{ep}]')}
    taken_name |= set(os.listdir(FR)) - {r['fr'] for r in todo}

    # 按内容真实秒排序(次序即画面先后), 同秒按原时间戳先后
    todo.sort(key=lambda r: (r['true'], r['cur']))
    plan, failed = [], []
    for r in todo:
        cand = r['true']
        # 依次向后找空闲秒; 越界(超过视频长度)则放弃
        while cand <= dur and (cand in taken or f'{ep}_{ts_of(cand)}.jpg' in taken_name):
            cand += 1
        if cand > dur:
            failed.append((r, '视频长度内无空闲秒'))
            continue
        nm = f'{ep}_{ts_of(cand)}.jpg'
        taken.add(cand)
        taken_name.add(nm)
        plan.append((r, cand, nm))
        if apply:
            r['e']['timestamp'] = ts_of(cand)
            if nm != r['fr']:
                os.rename(os.path.join(FR, r['fr']), os.path.join(FR, nm))
    if apply:
        json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    lines = [f'{ep} 重排: 改动 {len(plan)} / 共 {len(data)} 条, 未处理 {len(nopeak)} 条, 放置失败 {len(failed)} 条'
             + ('(已落盘)' if apply else '(预演)')]
    if filled:
        lines.append(f'  其中 {len(filled)} 条因越界且定位不清晰, 用邻居偏移插值:')
        for e, cur, tgt, off in filled:
            lines.append(f"     {e['timestamp']:>7s} -> {ts_of(tgt)} (插值偏移{off:+d}s) {e.get('text', '')[:24]}")
    for r, cand, nm in plan:
        d = cand - r['true']
        lines.append(f"  {r['e']['timestamp']:>7s} -> {ts_of(cand):>7s} (内容{ts_of(r['true'])}, 位移{d:+d}s) "
                     f"{r['e'].get('text', '')[:26]:28s} {r['fr']} -> {nm}")
    for r, why in failed:
        lines.append(f"  !! {r['e']['timestamp']:>7s} 放置失败: {why}  {r['e'].get('text', '')[:24]}")
    for e, fr, why in nopeak:
        lines.append(f"  ?? {e['timestamp']:>7s} 未处理: {why}  {e.get('text', '')[:24]}  frame={fr}")
    if minor:
        lines.append(f'  -- 另有 {len(minor)} 条偏移 1~{OFF_MIN - 1}s, 视为可接受未改动:')
        for r, d in sorted(minor, key=lambda x: x[1])[:20]:
            lines.append(f"     {r['e']['timestamp']:>7s} (内容{ts_of(r['true'])}, {d:+d}s) {r['e'].get('text', '')[:24]}")
    txt = '\n'.join(lines)
    open(os.path.join(B, 'review', f'retime_{ep}.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
