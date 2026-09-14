# -*- coding: utf-8 -*-
"""q_revert.py — 回退经原片复核证伪的历史修正。

第 4 轮用"按库时间戳直接读原片"对全库 184 条已落盘修正做反向审计, 发现 2 条是
**前几轮改错的**(判定依据是 960×540 帧图或错位的回退帧):

  P02 9m50s  [朝阳你先回家去] -> [朝阳你先回家]
      原判"画面无去字"; 实测 t=590.0 / 590.4s 两处 bin/raw 四路读数全部为「朝阳你先回家去」
  P04 3m39s  [嗯说的没错] -> [说的没错]
      原判"首字噪声"; 实测 t=219.0~219.8s 五点读数均为「嗯说的没错」(bin 把 嗯 误读成 咽,
      raw 读成「一嗯说的没错」, 那个"一"是 嗯 的左缘), 嗯 是真实语气词

用法: python q_revert.py [--dry]
输出: 改 subtitle_clean/*.json + review/q_revert_result.json
"""
import json
import os
import shutil
import sys
import time

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle_clean')

REVERTS = [
    {'ep': 'P02', 'ts': '9m50s', 'cur': '朝阳你先回家', 'back': '朝阳你先回家去',
     'why': '原片 t=590.0/590.4s 四路读数均为[朝阳你先回家去], 原修正"画面无去字"系帧图误判'},
    {'ep': 'P04', 'ts': '3m39s', 'cur': '说的没错', 'back': '嗯说的没错',
     'why': '原片 t=219.0~219.8s 五点读数均为[嗯说的没错], 嗯 为真实语气词, 原判"首字噪声"有误'},
]


def main():
    dry = '--dry' in sys.argv
    applied, bad = [], []
    by_ep = {}
    for r in REVERTS:
        by_ep.setdefault(r['ep'], []).append(r)
    for ep, recs in sorted(by_ep.items()):
        fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]') and f.endswith('.json')][0]
        p = os.path.join(CLEAN, fn)
        data = json.load(open(p, encoding='utf-8'))
        idx = {e.get('timestamp'): e for e in data}
        n = 0
        for r in recs:
            e = idx.get(r['ts'])
            if e is None or e.get('text') != r['cur']:
                bad.append({'ep': ep, 'ts': r['ts'], 'lib': e.get('text') if e else None,
                            'expect': r['cur']})
                continue
            e['text'] = r['back']
            applied.append({'ep': ep, 'ts': r['ts'], 'from': r['cur'], 'to': r['back'],
                            'why': r['why']})
            n += 1
        if n and not dry:
            shutil.copy2(p, p + '.bak_qrevert')
            json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'  {ep}: 回退 {n} 条')
    out = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'dry': dry,
           'n': len(applied), 'reverted': applied, 'mismatch': bad}
    if dry:
        # 预演**不能写结果文件** —— 它会被写成 reverted: [], 让 q_audit 把已回退的 2 条
        # 重新当成"异常"(实际踩过这个坑)。
        print(f"合计回退 {len(applied)} 条（预演, 未写盘）/ 不匹配 {len(bad)} 条")
        return
    json.dump(out, open(os.path.join(REVIEW, 'q_revert_result.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"合计回退 {len(applied)} 条 / 不匹配 {len(bad)} 条")
    for a in applied:
        print(f"  {a['ep']} {a['ts']:>7s} [{a['from']}] -> [{a['to']}]")


if __name__ == '__main__':
    main()
