# -*- coding: utf-8 -*-
"""rollback_risky_applied.py — 回滚「完全不同台词」类应用（前后句保护）

用户指出：P06 五香粉→红辣椒、P19 达令→明白 都是前后句关系，
我凭单帧画面把相邻台词误当错文本覆盖。系统性修复：
  对 vision_applied_log.json 每条：
    from/to 净 CJK LCS >= 0.65  → 同句小改，保留
    LCS < 0.65                  → 高风险（前后句/误读），回滚 from
  回滚后对邻接 ±3s 同文本做去重；输出清单。
"""
import difflib
import glob
import json
import os
import re

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
LOG = os.path.join(BASE, 'review', 'vision_applied_log.json')
CJK_RE = re.compile(r'[\u4e00-\u9fff]')
NOISE = ('bilibili', '正版', '正饭', '正服', '脂', '円谷', 'テレビ', 'クワトロ',
         'MSelect', 'リンデ', 'アゼン', 'シリーズ')


def cjk(t):
    return ''.join(CJK_RE.findall(t))


def lcs_ratio(a, b):
    m, n = len(a), len(b)
    if not m or not n:
        return 0
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i][j - 1], dp[i - 1][j])
    return dp[m][n] / min(m, n)


def is_noise(t):
    return t and any(n in t for n in NOISE)


def main():
    log = json.load(open(LOG, encoding='utf-8'))
    keep, rollback = [], []
    for x in log:
        f, t = cjk(x['from']), cjk(x['to'])
        r = lcs_ratio(f, t)
        if r >= 0.65:
            keep.append(x)
        else:
            rollback.append({**x, 'lcs': round(r, 2)})
    print(f'保留应用 {len(keep)} | 回滚 {len(rollback)}', flush=True)

    # 回滚 from（仅当 from 是干净中文且非噪声）
    by_ep = {}
    for x in rollback:
        if not x['from'] or is_noise(x['from']):
            # 乱码类不回滚（保持新文本），仅审计
            continue
        by_ep.setdefault(x['ep'], []).append(x)
    n_rb = 0
    rb_log = []
    for ep, items in by_ep.items():
        fs = [f for f in glob.glob(os.path.join(CLEAN_DIR, '*.json'))
              if os.path.basename(f).startswith(f'[{ep}]')]
        if not fs:
            continue
        data = json.load(open(fs[0], encoding='utf-8'))
        by_ts = {x['ts']: x['from'] for x in items}
        for r in data:
            ts = r.get('timestamp')
            if ts in by_ts and r.get('text') != by_ts[ts]:
                r['text'] = by_ts[ts]
                n_rb += 1
                rb_log.append({'ep': ep, 'ts': ts, 'restored': by_ts[ts][:36]})
        # 邻接 ±3s 同文本去重（回滚后 may produce dup）
        data_sorted = sorted(data, key=lambda r: int(r.get('timestamp', '0m0s').rstrip('s').split('m')[0]) * 60
                             + int(r.get('timestamp', '0m0s').split('m')[1].rstrip('s')))
        seen = {}
        to_del = []
        for r in data_sorted:
            ts = r.get('timestamp', '')
            m = ts.split('m')
            s = int(m[0]) * 60 + int(m[1].rstrip('s')) if len(m) == 2 else -1
            txt = r.get('text', '')
            for s2, t2 in list(seen.items()):
                if abs(s - s2) <= 3 and t2 == txt:
                    to_del.append(r)
                    break
            seen[s] = txt
        data = [r for r in data if r not in to_del]
        json.dump(data, open(fs[0], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{ep}: 回滚 {len(items)} 条/{len(data)}')

    with open(os.path.join(BASE, 'review', 'rollback_risky.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'rollback': rb_log,
                   'kept': keep,
                   'not_restored_noise': [x for x in rollback if is_noise(x['from'])]},
                  fh, ensure_ascii=False, indent=1)
    print(f'实际回滚 {n_rb} 条；审计 review/rollback_risky.json')


if __name__ == '__main__':
    main()
