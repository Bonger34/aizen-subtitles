# -*- coding: utf-8 -*-
"""q_apply.py — 把 q_align_tl.py 判定为 apply_add 的高置信修正落盘到 subtitle_clean。

只应用"纯插入"型修正(旧文本字符全保留、新文本多出字符), 这类实测方向可靠;
其余(del/replace/mixed)一律不动, 输出到 review 清单供人工核对。

用法: python q_apply.py [--dry] [--verdicts apply_add]
输出: 修改 subtitle_clean/*.json + 审计 review/q_apply_result.json
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
    verdicts = ['apply_add']
    if '--verdicts' in sys.argv:
        verdicts = sys.argv[sys.argv.index('--verdicts') + 1].split(',')
    src = os.path.join(REVIEW, 'q_align_tl.json')
    if not os.path.exists(src):
        raise SystemExit('缺少 review/q_align_tl.json, 先跑 q_align_tl.py')
    detail = json.load(open(src, encoding='utf-8'))
    # 人工核对结果(对照 review/q_sheet_*.jpg): reject 的丢弃, fix 的替换新文本
    man_p = os.path.join(REVIEW, 'q_manual_verdicts.json')
    reject, fix = set(), {}
    if os.path.exists(man_p):
        man = json.load(open(man_p, encoding='utf-8'))
        reject = {(r['ep'], r['ts']) for r in man.get('reject', [])}
        fix = {(r['ep'], r['ts']): r['new'] for r in man.get('fix', [])}
        print(f'人工核对清单: 拒绝 {len(reject)} 条, 修正 {len(fix)} 条')
    else:
        print('警告: 未找到 review/q_manual_verdicts.json, 将不加人工过滤')

    by_ep = {}
    n_rej = 0
    for ep, d in detail.items():
        for r in d['items']:
            if r.get('verdict') in verdicts and r.get('new'):
                if (ep, r['ts']) in reject:
                    n_rej += 1
                    continue
                r = dict(r, new=fix.get((ep, r['ts']), r['new']))
                by_ep.setdefault(ep, []).append(r)
    print(f'人工拒绝 {n_rej} 条')

    applied, missing = [], []
    for ep, recs in sorted(by_ep.items()):
        fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]
        p = os.path.join(CLEAN, fn)
        data = json.load(open(p, encoding='utf-8'))
        idx = {e.get('timestamp'): e for e in data}
        n = 0
        for r in recs:
            e = idx.get(r['ts'])
            if e is None:
                missing.append({'ep': ep, 'ts': r['ts'], 'why': 'timestamp_not_found'})
                continue
            if e.get('text') != r['old']:
                missing.append({'ep': ep, 'ts': r['ts'], 'why': 'old_text_changed',
                                'lib': e.get('text'), 'expect': r['old']})
                continue
            applied.append({'ep': ep, 'ts': r['ts'], 'from': r['old'], 'to': r['new'],
                            'sim': r['best_sim'], 'support': r['support'], 'dt': r.get('dt')})
            e['text'] = r['new']
            n += 1
        if n and not dry:
            shutil.copy2(p, p + '.bak_qapply')
            json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{ep}: 应用 {n} 条' + ('(预演)' if dry else ''))

    out = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'dry': dry, 'verdicts': verdicts,
           'n_applied': len(applied), 'applied': applied, 'missing': missing}
    json.dump(out, open(os.path.join(REVIEW, 'q_apply_result.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"\n合计应用 {len(applied)} 条 / 跳过 {len(missing)} 条"
          f"{'(预演, 未落盘)' if dry else ''}")
    for a in applied[:40]:
        print(f"  {a['ep']} {a['ts']:>7s} sup={a['support']} [{a['from']}] -> [{a['to']}]")
    print('审计: review/q_apply_result.json')


if __name__ == '__main__':
    main()
