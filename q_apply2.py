# -*- coding: utf-8 -*-
"""q_apply2.py — 应用"帧图 × 时间线 双源互证"的文本修正(人工逐条核对后的清单)。

清单来源: review/q_verify_review.json 中 sim_frame_new>=0.98 且 sim_frame_old<0.98 的 61 条,
逐条对照 review/q_sheetv_strict_*.jpg 由人工判定 —— 其中相当一部分是"帧图漏读尾部/开头"
造成的假修正(如 罗布奥特曼->罗布奥特), 因此不能自动应用, 只落盘人工确认的部分。
用法: python q_apply2.py [--dry]
"""
import json
import os
import shutil
import sys
import time

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle_clean')


def main():
    dry = '--dry' in sys.argv
    man = json.load(open(os.path.join(REVIEW, 'q_manual_verdicts.json'), encoding='utf-8'))
    items = man.get('frame_apply', [])
    print(f'待应用 {len(items)} 条')
    by_ep = {}
    for r in items:
        by_ep.setdefault(r['ep'], []).append(r)
    applied, bad = [], []
    for ep, recs in sorted(by_ep.items()):
        fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]
        p = os.path.join(CLEAN, fn)
        data = json.load(open(p, encoding='utf-8'))
        idx = {e.get('timestamp'): e for e in data}
        n = 0
        for r in recs:
            e = idx.get(r['ts'])
            if e is None or e.get('text') != r['old']:
                bad.append({'ep': ep, 'ts': r['ts'], 'lib': e.get('text') if e else None,
                            'expect': r['old']})
                continue
            e['text'] = r['new']
            applied.append({'ep': ep, 'ts': r['ts'], 'from': r['old'], 'to': r['new'],
                            'why': r.get('why', '')})
            n += 1
        if n and not dry:
            shutil.copy2(p, p + '.bak_qapply2')
            json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'  {ep}: {n} 条')
    out_p = os.path.join(REVIEW, 'q_apply2_result.json')
    prev = json.load(open(out_p, encoding='utf-8')).get('applied', []) if os.path.exists(out_p) else []
    merged = {(a['ep'], a['ts']): a for a in prev}
    for a in applied:
        merged[(a['ep'], a['ts'])] = a
    all_applied = sorted(merged.values(), key=lambda a: (a['ep'], a['ts']))
    out = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'dry': dry,
           'n_applied': len(all_applied), 'n_this_run': len(applied),
           'applied': all_applied, 'mismatch': bad}
    json.dump(out, open(out_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\n合计 {len(applied)} 条{'（预演）' if dry else ''} / 不匹配 {len(bad)} 条")
    for a in applied:
        print(f"  {a['ep']} {a['ts']:>7s} [{a['from']}] -> [{a['to']}]")
    if bad:
        print('不匹配:', bad)


if __name__ == '__main__':
    main()
