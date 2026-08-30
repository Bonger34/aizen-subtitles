# -*- coding: utf-8 -*-
"""apply_vision_verdicts.py — 批量应用视觉核定结果

verdicts (262 条) 每条含 id + vt(画面真实文本) + note。
应用规则：
  note 含 "采纳new" / "vt修正" → 库文本替换为 vt（画面核定文本）
  note 含 "保留old"          → 不动
输出统计 + 重写 subtitle_clean + 生成审计。
"""
import glob
import json
import os

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
VERDICTS = os.path.join(BASE, 'review', 'ocr_vision_verdicts.json')


def main():
    verdicts = json.load(open(VERDICTS, encoding='utf-8'))
    print('判定总数:', len(verdicts))
    n_apply = n_keep = n_same = 0
    by_ep = {}
    for v in verdicts:
        note = v.get('note', '')
        apply = ('采纳new' in note or 'vt修正' in note) and note != '保留old'
        if not apply:
            n_keep += 1
            continue
        ep = v['id'].rsplit('_', 1)[0]
        by_ep.setdefault(ep, []).append(v)

    applied_log = []
    for ep, items in by_ep.items():
        fs = [f for f in glob.glob(os.path.join(CLEAN_DIR, '*.json'))
              if os.path.basename(f).startswith(f'[{ep}]')]
        if not fs:
            continue
        data = json.load(open(fs[0], encoding='utf-8'))
        by_ts = {v['id'].split('_', 1)[1]: v['vt'] for v in items}
        n = 0
        for r in data:
            ts = r.get('timestamp')
            if ts in by_ts:
                new = by_ts[ts]
                if r.get('text') != new:
                    applied_log.append({'ep': ep, 'ts': ts, 'from': r.get('text', '')[:30],
                                        'to': new[:30]})
                    r['text'] = new
                    n += 1
                else:
                    n_same += 1
        json.dump(data, open(fs[0], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{ep}: 应用 {n}')
        n_apply += n

    print(f'\n应用 {n_apply} | 已一致 {n_same} | 保留 {n_keep}')
    with open(os.path.join(BASE, 'review', 'vision_applied_log.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(applied_log, fh, ensure_ascii=False, indent=1)
    print('审计: review/vision_applied_log.json')


if __name__ == '__main__':
    main()
