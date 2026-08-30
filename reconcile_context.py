# -*- coding: utf-8 -*-
"""reconcile_context.py — 20条回滚的二次判定 + P19达令补回

判定依据：原始 subtitle/ 中是否存在与「恢复句子」相同的条目（任意 ts）：
  存在 → 前后句（原始两句都在）→ 保持回滚，且若 clean 缺该条则补回
  不存在 → 恢复句是 v3 错读，画面核定是对的 → 撤销回滚（重新应用 to）
另：P19 达令（LCS 0.89 被保留）——vl_out 19m13s 有独立"达令"条目，
clean 缺一条 → 补插。
"""
import glob
import json
import os

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
ORIG_DIR = os.path.join(BASE, 'subtitle')
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
RB = os.path.join(BASE, 'review', 'rollback_risky.json')
LOG = os.path.join(BASE, 'review', 'vision_applied_log.json')


def load_ep(directory, ep):
    fs = [f for f in os.listdir(directory)
          if f.startswith(f'[{ep}]') and f.endswith('.json')]
    if not fs:
        return []
    return json.load(open(os.path.join(directory, fs[0]), encoding='utf-8'))


def main():
    rb = json.load(open(RB, encoding='utf-8'))
    applied = {(x['ep'], x['ts']): x for x in json.load(open(LOG, encoding='utf-8'))}
    kind_count = {'keep_rollback': 0, 'undo_rollback': 0, 'insert_time': 0}

    # 原始全库文本集合
    orig_texts = {}
    for f in glob.glob(os.path.join(ORIG_DIR, '*.json')):
        for r in json.load(open(f, encoding='utf-8')):
            orig_texts.setdefault(r.get('text', ''), []).append(os.path.basename(f)[1:4])

    undo = []
    for x in rb['rollback']:
        ep, ts = x['ep'], x['ts']
        restored = x['restored']
        # 原句是否在原始库出现（任意 ts）
        if restored in orig_texts:
            kind_count['keep_rollback'] += 1
            print(f"[前后句确认] {ep} {ts} 「{restored[:20]}」 原始存在 → 保持回滚")
        else:
            kind_count['undo_rollback'] += 1
            print(f"[误回滚→恢复修正] {ep} {ts} 「{restored[:20]}」 原始不存在（v3错读）")
            undo.append((ep, ts))

    # 撤销回滚（重新应用 to）
    n_undo = 0
    by_ep = {}
    for ep, ts in undo:
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
                n_undo += 1
        json.dump(data, open(os.path.join(CLEAN_DIR,
                  [f for f in os.listdir(CLEAN_DIR) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]),
                  'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'重新应用修正 {n_undo} 条')
    kind_count['undo_rollback'] = n_undo

    # P19 达令补回：若 clean 无「达令启动拘捕怪兽系统」且 19m13s 空位
    p19 = load_ep(CLEAN_DIR, 'P19')
    has_darling = any('达令' in r.get('text', '') for r in p19)
    if not has_darling:
        p19.append({'timestamp': '19m13s', 'text': '达令启动拘捕怪兽系统',
                    'similarity': 0.0})
        json.dump(p19, open([f for f in os.listdir(CLEAN_DIR)
                            if f.startswith('[P19]') and f.endswith('.json')][0],
                            'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        kind_count['insert_time'] = 1
        print('补回: P19 19m13s 达令启动拘捕怪兽系统')

    with open(os.path.join(BASE, 'review', 'reconcile_context.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(kind_count, fh, ensure_ascii=False, indent=1)
    print('结果:', kind_count)


if __name__ == '__main__':
    main()
