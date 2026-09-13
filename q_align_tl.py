# -*- coding: utf-8 -*-
"""q_align.py — 把全片字幕时间线(q_timeline_<EP>.json)与库条目对齐, 判定每条文本该不该改。

判定与 q_judge.py 同口径: 只有"新文本与旧文本字符级高度相似"才说明读到同一句(同源),
此时差异才可信; 读到别句时相似度通常 <0.5。差异再按编辑操作分型:
  纯插入(旧文本是新文本的子序列) -> apply_add   例如 在年前的今天 -> 在15年前的今天
  纯删除(新文本是旧文本的子序列) -> apply_del
  含替换                          -> review      需要人工看图, 因为替换方向无法自动判定
用法: python q_align.py P01 [P02 ...] [--win 6]
输出: review/q_align_tl_<EP>.json + review/q_align_tl.txt
"""
import json
import os
import sys
from collections import defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q_common import kana_ratio, norm, sim, to_simp  # noqa: E402

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle_clean')
CLUSTER = 0.90     # 同一句的多次识别视为一条
CONFIRM = 0.95
SRC_LO = 0.55
EVENT_GAP = 1.6    # 相邻 OCR 点间隔超过此值(秒) -> 切成两个字幕事件


def parse_ts(ts):
    import re
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def cluster(texts, thr=CLUSTER):
    """把多次识别结果按相似度归并, 返回 [(代表文本, 出现次数, 平均置信度)]。"""
    reps = []
    for t, sc in texts:
        for r in reps:
            if sim(t, r[0]) >= thr:
                r[1] += 1
                r[2].append(sc)
                break
        else:
            reps.append([t, 1, [sc]])
    reps.sort(key=lambda r: -r[1])
    return [(r[0], r[1], round(sum(r[2]) / len(r[2]), 3)) for r in reps]


def build_events(tl, paths, sim_join=0.80):
    """把时间线中 ocr=true 的采样点合并成字幕事件。

    合并判据用"文本相似度"而不是时间间隔 —— 连续对话时字幕一句接一句(间隔 <1s),
    若按间隔合并会把多句并成一个事件, 实测会导致事件数只有真实句数的 1/4。
    """
    pts = [p for p in tl['points'] if p.get('ocr') and p.get('segs')]
    for p in pts:
        p['_texts'] = [t for s in p['segs'] for path in paths
                       if (t := (s.get(path) or '').strip())]
    events, cur = [], []
    for p in pts:
        if cur and p['_texts'] and cur[-1]['_texts']:
            same = max(sim(a, b) for a in p['_texts'] for b in cur[-1]['_texts'])
        else:
            same = 0.0
        if cur and same < sim_join:
            events.append(cur)
            cur = []
        cur.append(p)
    if cur:
        events.append(cur)
    out = []
    for grp in events:
        texts = [(t, 0.0) for p in grp for t in p['_texts']]
        if not texts:
            continue
        texts = [(to_simp(t), s) for t, s in texts]
        cl = cluster(texts)
        out.append({'t0': grp[0]['t'], 't1': grp[-1]['t'],
                    'mid': round((grp[0]['t'] + grp[-1]['t']) / 2, 2),
                    'n_pts': len(grp), 'n_read': len(texts),
                    'text': cl[0][0], 'support': cl[0][1],
                    'alts': [{'text': c[0], 'n': c[1]} for c in cl[1:4]]})
    return out


def edit_kind(old, new):
    """返回 (类型, 说明)。类型: same/add/del/replace/mixed。"""
    a, b = norm(old), norm(new)
    sm = SequenceMatcher(None, a, b, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
    kinds = {o[0] for o in ops}
    if not kinds:
        return 'same', ''
    ins = sum(o[4] - o[3] for o in ops if o[0] == 'insert')
    dele = sum(o[2] - o[1] for o in ops if o[0] == 'delete')
    rep = sum(max(o[2] - o[1], o[4] - o[3]) for o in ops if o[0] == 'replace')
    desc = ';'.join(f"{o[0]}:{a[o[1]:o[2]]}->{b[o[3]:o[4]]}" for o in ops)
    if kinds == {'insert'}:
        return 'add', f'+{ins} {desc}'
    if kinds == {'delete'}:
        return 'del', f'-{dele} {desc}'
    if kinds == {'replace'}:
        return 'replace', f'~{rep} {desc}'
    return 'mixed', desc


def align_ep(ep, win, paths=('bin', 'raw')):
    tl_p = os.path.join(REVIEW, f'q_timeline_{ep}.json')
    if not os.path.exists(tl_p):
        return None
    tl = json.load(open(tl_p, encoding='utf-8'))
    paths = tl.get('paths', paths)
    events = build_events(tl, paths)
    fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]
    data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))

    # 贪心互斥匹配: 按相似度从高到低占用事件
    pairs = []
    for i, e in enumerate(data):
        sec, old = parse_ts(e.get('timestamp')), e.get('text', '')
        if sec is None:
            continue
        for j, ev in enumerate(events):
            if abs(ev['mid'] - sec) > win:
                continue
            s = sim(ev['text'], old)
            if s > 0:
                pairs.append((s, i, j))
    pairs.sort(key=lambda z: -z[0])
    used_i, used_j = {}, set()
    for s, i, j in pairs:
        if i in used_i or j in used_j:
            continue
        used_i[i] = (j, s)
        used_j.add(j)

    recs = []
    for i, e in enumerate(data):
        old = e.get('text', '')
        raw = {'ts': e.get('timestamp'), 'old': old, 'verdict': 'unmatched'}
        if i in used_i:
            j, s = used_i[i]
            ev = events[j]
            raw.update({'best_sim': round(s, 3), 'new': ev['text'], 'support': ev['support'],
                        'ts_video': ev['mid'], 'dt': round(ev['mid'] - (parse_ts(e['timestamp']) or 0), 2),
                        'n_read': ev['n_read'], 'alts': ev['alts']})
            if s >= CONFIRM:
                raw['verdict'] = 'confirmed'
            elif s < SRC_LO:
                raw['verdict'] = 'unmatched'
            else:
                kind, desc = edit_kind(old, ev['text'])
                raw.update({'kind': kind, 'desc': desc, 'kana': round(kana_ratio(ev['text']), 2)})
                # 只有"纯插入"方向可信: 旧文本字符全部保留、新文本多出字符(实测 4/4 正确);
                # "纯删除"其实多数是新文本漏字(如 就你了罗布水晶 -> 了罗布水晶), 一律转人工。
                if kind == 'same':
                    raw['verdict'] = 'confirmed'
                elif kind == 'add' and ev['support'] >= 2 and raw['kana'] <= 0.15:
                    raw['verdict'] = 'apply_add'
                else:
                    raw['verdict'] = 'review'
        recs.append(raw)
    return {'ep': ep, 'src': f'q_timeline_{ep}.json', 'n_events': len(events),
            'n_entries': len(data), 'items': recs}


def main():
    args = sys.argv[1:]
    win = float(args[args.index('--win') + 1]) if '--win' in args else 6.0
    eps = [a for a in args if not a.startswith('-')]
    if not eps:
        eps = sorted(f[len('q_timeline_'):-5] for f in os.listdir(REVIEW)
                     if f.startswith('q_timeline_') and f.endswith('.json'))
    detail, summ = {}, defaultdict(int)
    for ep in eps:
        d = align_ep(ep, win)
        if d is None:
            print(f'{ep}: 无时间线')
            continue
        detail[ep] = d
        for r in d['items']:
            summ[r['verdict']] += 1
        c = defaultdict(int)
        for r in d['items']:
            c[r['verdict']] += 1
        print(f"{ep}: 事件 {d['n_events']} / 条目 {d['n_entries']} | " +
              ' '.join(f'{k}={v}' for k, v in sorted(c.items())))
    json.dump(detail, open(os.path.join(REVIEW, 'q_align_tl.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    lines = []
    for ep, d in detail.items():
        lines.append(f'===== {ep}')
        for r in d['items']:
            if r['verdict'] in ('apply_add', 'apply_del', 'review'):
                lines.append(f"  [{r['verdict']}/{r.get('kind')}] {r['ts']:>7s} "
                             f"sim={r['best_sim']:.2f} sup={r.get('support')} "
                             f"dt={r.get('dt'):+.2f}s {r.get('desc', '')}")
                lines.append(f"        旧[{r['old']}]")
                lines.append(f"        新[{r['new']}]")
            elif r['verdict'] == 'unmatched':
                lines.append(f"  [unmatched] {r['ts']:>7s} 旧[{r['old']}]")
    open(os.path.join(REVIEW, 'q_align_tl.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('\n汇总:', dict(summ))
    print('明细: review/q_align_tl.json + review/q_align_tl.txt')


if __name__ == '__main__':
    main()
