# -*- coding: utf-8 -*-
"""q_audit.py — 从 subtitle 反查全部文本修正是否已落盘, 生成统一审计文件。

不依赖各次运行的中间结果(它们可能被后续运行覆盖), 直接以库内容为准:
  读 review/q_apply_result.json(apply_add 76 条) 与 review/q_manual_verdicts.json(frame_apply 36 条),
  逐条核对库里该 timestamp 的当前文本是否等于目标新文本。
输出: review/q_fixes_final.json + 控制台汇总

2026-09 起还要读 review/q_retime_applied.json: 那是一次时间戳重排的记录
(255 条条目的 timestamp 被改成实测到的真实秒)。修正记录里的 (集, 时间戳) 是**重排前**的,
所以按老时间戳查不到 —— 命中不到时用重排表换算出新时间戳再查一次。
不这样做的话这 17 条会被长期误报成"异常", 掩盖真正的漏落盘。
"""
import json
import os
from collections import Counter, defaultdict

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle')

fixes = []
p1 = os.path.join(REVIEW, 'q_apply_result.json')
if os.path.exists(p1):
    for a in json.load(open(p1, encoding='utf-8')).get('applied', []):
        fixes.append({'ep': a['ep'], 'ts': a['ts'], 'old': a['from'], 'new': a['to'],
                      'src': 'apply_add', 'sim': a.get('sim'), 'support': a.get('support')})
p2 = os.path.join(REVIEW, 'q_manual_verdicts.json')
if os.path.exists(p2):
    for a in json.load(open(p2, encoding='utf-8')).get('frame_apply', []):
        fixes.append({'ep': a['ep'], 'ts': a['ts'], 'old': a['old'], 'new': a['new'],
                      'src': 'frame_apply', 'why': a.get('why')})

lib = {}
for fn in os.listdir(CLEAN):
    if fn.endswith('.json'):
        ep = fn.split(']')[0].lstrip('[')
        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
            lib[(ep, e['timestamp'])] = e.get('text')

# 已回退的修正(review/q_revert_result.json)不算异常: 它们是经原片复核**主动撤销**的,
# 库里应当回到旧文本。不区分的话审计会长期报红, 掩盖真正的漏落盘。
reverted = set()
pr = os.path.join(REVIEW, 'q_revert_result.json')
if os.path.exists(pr):
    for r in json.load(open(pr, encoding='utf-8')).get('reverted', []):
        # 回退记录里 from=被撤销的修正文本, to=恢复后的原文本; 换算成 (ep, ts, 原文本, 修正文本)
        reverted.add((r['ep'], r['ts'], r['to'], r['from']))

# 时间戳重排表: (集, 重排前时间戳) -> 重排后时间戳。修正记录里的时间戳是重排前的,
# 直接用会查不到; 先按老时间戳查, 查不到再按重排后的查一次。
retimed = {}
prt = os.path.join(REVIEW, 'q_retime_applied.json')
if os.path.exists(prt):
    for r in json.load(open(prt, encoding='utf-8')):
        retimed[(r['ep'], r['old_ts'])] = r['new_ts']

applied, undone, problem = [], [], []
for f in fixes:
    cur = lib.get((f['ep'], f['ts']))
    if cur is None and (f['ep'], f['ts']) in retimed:
        # 该条被重排过: 文本应当出现在新时间戳上
        cur = lib.get((f['ep'], retimed[(f['ep'], f['ts'])]))
        if cur is not None:
            f = dict(f, ts=retimed[(f['ep'], f['ts'])], retimed_from=f['ts'])
    if cur == f['new']:
        applied.append(f)
    elif (f['ep'], f['ts'], f['old'], f['new']) in reverted and cur == f['old']:
        undone.append(dict(f, current=cur))
    else:
        problem.append(dict(f, current=cur))

by_src, by_ep = Counter(), Counter()
for a in applied:
    by_src[a['src']] += 1
    by_ep[a['ep']] += 1
out = {'n_total': len(fixes), 'n_applied': len(applied), 'n_reverted': len(undone),
       'n_problem': len(problem), 'by_src': dict(by_src), 'by_ep': dict(sorted(by_ep.items())),
       'applied': applied, 'reverted': undone, 'problem': problem}
json.dump(out, open(os.path.join(REVIEW, 'q_fixes_final.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f"修正总数 {len(fixes)} | 已落盘 {len(applied)} | 已回退 {len(undone)} | 异常 {len(problem)}")
print('来源分布:', dict(by_src))
print('按集:', dict(sorted(by_ep.items())))
if undone:
    for p in undone:
        print('  已回退:', p['ep'], p['ts'], f"[{p['old']}] -> [{p['new']}]")
if problem:
    for p in problem[:10]:
        print('  异常:', p)
