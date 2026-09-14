# -*- coding: utf-8 -*-
"""q_suspect.py — 处理帧图重抽失败的"疑似正片台词"清单(150 条)。

这 150 条的共性是: t±1.6s 内**找不到**任何一帧字幕与库文本一致。两条可能:
  (a) 库文本在这条上确实错;  (b) 漂移超过窗口 / 该句难被 OCR 读出。

判据用**顺序对齐**, 不用时间戳(库时间戳漂移非单调, 实测同集内既有 +1s 也有 -2.5s):
找到本条目的上一条/下一条库文本在全片时间线里各自对应的字幕事件, 则"夹在两者之间、
且尚未被任何库条目认领"的那个事件就是本条目的真实文本。

用法: python q_suspect.py [--win 8]
输出: review/q_suspect.json + 控制台清单
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q_align_tl import build_events          # noqa: E402
from q_common import is_subseq, norm, sim    # noqa: E402

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle_clean')
FR_FIX = os.path.join(B, 'Web', 'frames_fix')


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def load_lib(ep):
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]
    return json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))


def scope(old, ts):
    """带外判定: 版权卡 / 日文 / 片尾 / 碎片噪声。"""
    KANA = set(range(0x3040, 0x30FF))
    t = old or ''
    if '版权' in t or '中国大陆' in t:
        return '版权卡'
    if sum(1 for c in t if ord(c) in KANA) / max(1, len(t)) > 0.15:
        return '日文'
    if (parse_ts(ts) or 0) >= 21 * 60 + 30:
        return '片尾'
    if len(norm(t)) <= 2:
        return '碎片'
    return 'in'


def main():
    win = 8.0
    if '--win' in sys.argv:
        win = float(sys.argv[sys.argv.index('--win') + 1])

    tg = json.load(open(os.path.join(REVIEW, 'q_reframe_tg.json'), encoding='utf-8'))
    got = set(os.listdir(FR_FIX))
    miss = [r for r in tg if r.get('frame') not in got and scope(r['old'], r['ts']) == 'in']
    print(f'帧图重抽失败且属正片范围: {len(miss)} 条')

    by_ep = defaultdict(list)
    for r in miss:
        by_ep[r['ep']].append(r)

    out = []
    for ep in sorted(by_ep):
        lib = load_lib(ep)
        tl = json.load(open(os.path.join(REVIEW, f'q_timeline_{ep}.json'), encoding='utf-8'))
        events = build_events(tl, tl.get('paths', ['bin', 'raw']))
        idx = {e.get('timestamp'): i for i, e in enumerate(lib)}
        # 事件 vs 库条目 的贪心互斥匹配(与 q_align_tl 同口径), 用于判断哪些事件已被认领
        pairs = []
        for i, e in enumerate(lib):
            sec = parse_ts(e.get('timestamp'))
            if sec is None:
                continue
            for j, ev in enumerate(events):
                if abs(ev['mid'] - sec) > 6:
                    continue
                s = sim(ev['text'], e.get('text', ''))
                if s > 0.5:
                    pairs.append((s, i, j))
        pairs.sort(key=lambda z: -z[0])
        used_i, used_j = {}, set()
        for s, i, j in pairs:
            if i in used_i or j in used_j:
                continue
            used_i[i] = (j, s)
            used_j.add(j)

        for r in sorted(by_ep[ep], key=lambda x: parse_ts(x['ts']) or 0):
            i = idx.get(r['ts'])
            if i is None:
                continue
            sec = parse_ts(r['ts'])
            prev = lib[i - 1].get('text', '') if i > 0 else ''
            nxt = lib[i + 1].get('text', '') if i + 1 < len(lib) else ''
            near = [ev for ev in events if abs(ev['mid'] - sec) <= win]
            new = [ev for ev in near if not any(ev is events[j] for j in used_j)]
            # --- 顺序夹逼: 上一条/下一条库条目各自认领了哪个字幕事件, 本条目的真实文本
            #     必然落在两者之间(库时间戳不可靠, 但库条目与字幕的先后顺序是可靠的)
            jp = jn = None
            for k in range(i - 1, -1, -1):
                if k in used_i:
                    jp = used_i[k][0]
                    break
            for k in range(i + 1, len(lib)):
                if k in used_i:
                    jn = used_i[k][0]
                    break
            span = []
            if jp is not None and jn is not None and jp < jn:
                span = [events[j] for j in range(jp + 1, jn)
                        if j not in used_j and events[j]['mid'] > events[jp]['mid']
                        and events[j]['mid'] < events[jn]['mid']]
            # 候选 = 未被认领的事件里, 与旧文本"纯插入"关系(方向可靠)或最相似的
            best, bs = '', 0.0
            for ev in new:
                s = sim(ev['text'], r['old'])
                if s > bs:
                    best, bs = ev['text'], s
            addc = [ev['text'] for ev in new
                    if len(norm(ev['text'])) > len(norm(r['old'])) and is_subseq(r['old'], ev['text'])]
            out.append({'ep': ep, 'ts': r['ts'], 'old': r['old'], 'prev': prev, 'next': nxt,
                        'free': [{'t': ev['mid'], 'text': ev['text']} for ev in new],
                        'span': [{'t': ev['mid'], 'text': ev['text']} for ev in span],
                        'jp': jp, 'jn': jn,
                        'best': best, 'best_sim': round(bs, 3), 'add': addc})

    c = defaultdict(int)
    for r in out:
        c['有未认领事件' if r['free'] else '窗口内无未认领事件'] += 1
        if r['add']:
            c['其中含纯插入型候选'] += 1
    print('分档:', dict(c))

    adds = [r for r in out if r['add']]
    print(f'\n纯插入型候选 {len(adds)} 条(方向可靠, 仍需看图确认多出的字):')
    for r in adds:
        print(f"  {r['ep']} {r['ts']:>7s} [{r['old']}] -> {r['add'][:2]}")

    json.dump(out, open(os.path.join(REVIEW, 'q_suspect.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n输出: review/q_suspect.json')


if __name__ == '__main__':
    main()
