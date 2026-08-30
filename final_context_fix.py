# -*- coding: utf-8 -*-
"""final_context_fix.py — 同集判定 + P19窗口核对与修复"""
import glob
import json
import os

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
ORIG_DIR = os.path.join(BASE, 'subtitle')
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
RB = os.path.join(BASE, 'review', 'rollback_risky.json')
LOG = os.path.join(BASE, 'review', 'vision_applied_log.json')


def sec(ts):
    m = ts.split('m')
    return int(m[0]) * 60 + int(m[1].rstrip('s'))


def load_ep(d, ep):
    fs = [f for f in os.listdir(d) if f.startswith(f'[{ep}]') and f.endswith('.json')]
    if not fs:
        return []
    return json.load(open(os.path.join(d, fs[0]), encoding='utf-8'))


def main():
    # 原始按集文本集合
    orig_by_ep = {}
    for f in glob.glob(os.path.join(ORIG_DIR, '*.json')):
        ep = os.path.basename(f)[1:4]
        for r in json.load(open(f, encoding='utf-8')):
            orig_by_ep.setdefault(ep, set()).add(r.get('text', ''))

    rb = json.load(open(RB, encoding='utf-8'))
    applied = {(x['ep'], x['ts']): x for x in json.load(open(LOG, encoding='utf-8'))}
    undo2 = []
    for x in rb['rollback']:
        ep = x['ep']
        restored = x['restored']
        if restored in orig_by_ep.get(ep, set()):
            print(f"[同集确认 前后句] {ep} {x['ts']} 「{restored[:20]}」")
        else:
            print(f"[同集不存在→撤销回滚] {ep} {x['ts']} 「{restored[:20]}」")
            undo2.append((ep, x['ts']))

    # 撤销（重新应用 to）
    n = 0
    by_ep = {}
    for ep, ts in undo2:
        x = applied.get((ep, ts))
        if x:
            by_ep.setdefault(ep, []).append((ts, x['to']))
    for ep, items in by_ep.items():
        data = load_ep(CLEAN_DIR, ep)
        by_ts = dict(items)
        for r in data:
            ts = r.get('timestamp')
            if ts in by_ts and r.get('text') != by_ts[ts]:
                r['text'] = by_ts[ts]
                n += 1
        json.dump(data, open([f for f in os.listdir(CLEAN_DIR)
                             if f.startswith(f'[{ep}]') and f.endswith('.json')][0],
                             'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'撤销回滚恢复修正 {n} 条')

    # P19 窗口核查与修复（确保 13s 达令 + 15s 明白 两并存、无重复）
    p19 = load_ep(CLEAN_DIR, 'P19')
    win = sorted([r for r in p19 if 1140 <= sec(r.get('timestamp', '0m0s')) <= 1160],
                 key=lambda r: sec(r['timestamp']))
    print('P19 clean 现状:')
    for r in win:
        print(f"   {r['timestamp']}  {r['text'][:34]}")
    has_d = any('达令' in r.get('text', '') for r in p19)
    has_m = any(r.get('text', '').startswith('明白启动') for r in p19)
    if not has_d:
        p19.append({'timestamp': '19m13s', 'text': '达令启动拘捕怪兽系统', 'similarity': 0.0})
        print('补回 19m13s 达令…')
        json.dump(p19, open([f for f in os.listdir(CLEAN_DIR)
                            if f.startswith('[P19]') and f.endswith('.json')][0],
                            'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if not has_m:
        print('警告: P19 clean 无「明白启动」条目！')


if __name__ == '__main__':
    main()
