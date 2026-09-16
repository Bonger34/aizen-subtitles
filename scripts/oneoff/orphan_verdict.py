# -*- coding: utf-8 -*-
"""对 A 组孤儿帧做全库匹配:
  1) 本集全时段匹配(捕捉库时间戳偏移造成的假漏句)
  2) 全 25 集匹配(捕捉集号错标的帧)
残留 = 真正"库里没有的文本", 再分类为 日文/符号 还是 中文台词。
"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
ocr = json.load(open(os.path.join(B, 'review', 'orphan_ocr.json'), encoding='utf-8'))

libs = {}
for fn in os.listdir(CLEAN):
    m = re.match(r'\[(P\d+)\]', fn)
    if not m:
        continue
    rows = []
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        mm = re.match(r'(\d+)m(\d+)s', e.get('timestamp') or '')
        t = ''.join(re.findall(r'[\u4e00-\u9fff]', e.get('text') or ''))
        if mm and t:
            rows.append((int(mm.group(1)) * 60 + int(mm.group(2)), t))
    libs[m.group(1)] = rows
allrows = [(ep,) + r for ep, rows in libs.items() for r in rows]


def bef(tn, w):
    return sum(1 for c in tn if c in w) / len(tn) if tn and w else 0.0


def best(tn, pool, tau=0.6):
    top, arg = 0.0, None
    for r in pool:
        s = bef(tn, r[-1])
        if s > top:
            top, arg = s, r
    return top, arg


JPN = re.compile(r'[\u3040-\u30ff]')          # 假名 => 日文文本
report = []
residue = []
for tag in ('A', 'B'):
    rows = ocr[tag]
    stat = collections.Counter()
    for x in rows:
        tn = x['ocr']
        if len(tn) < 2:
            x['verdict'] = '空或单字'
            stat['空或单字'] += 1
            continue
        ep = x['f'][:3]
        s_local, a_local = best(tn, libs.get(ep, []))
        s_all, a_all = best(tn, allrows)
        if x['hit']:
            x['verdict'] = '窗口命中'
        elif s_local >= 0.6:
            x['verdict'] = f"本集另有匹配({a_local[0]//60}m{a_local[0]%60:02d}s)"
        elif s_all >= 0.6:
            x['verdict'] = f"全集库匹配({a_all[0]} {a_all[1]//60}m{a_all[1]%60:02d}s)"
        elif JPN.search(x['raw'] or ''):
            x['verdict'] = '日文文本(片尾/标题卡)'
        else:
            x['verdict'] = '残留待判'
            residue.append(x)
        x['best_local'] = round(s_local, 3)
        x['best_all'] = round(s_all, 3)
        stat[x['verdict'].split('(')[0]] += 1
    report.append(f'== {tag} 组 {len(rows)} 帧判定分布:')
    for k, v in stat.most_common():
        report.append(f'   {k}: {v}')

report.append(f'\n残留待判 {len(residue)} 条:')
for x in sorted(residue, key=lambda y: y['f']):
    report.append(f"   {x['f']:18s} wr={x['wr']:.3f} ocr=[{x['ocr']}] raw=[{(x['raw'] or '')[:60]}] "
                  f"local={x['best_local']} all={x['best_all']}")

json.dump(ocr, open(os.path.join(B, 'review', 'orphan_ocr.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
txt = '\n'.join(report)
open(os.path.join(B, 'review', 'orphan_verdict.txt'), 'w', encoding='utf-8').write(txt)
print(txt)
