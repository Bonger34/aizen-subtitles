# -*- coding: utf-8 -*-
"""对 765 条疑似台词做聚类与近邻分析, 收敛出真正的候选。

1) 按"文本相似(双向包含度>=0.7)"聚类 —— 同一句在不同秒被多次读到会合成一类;
2) 每类给出: 出现次数、代表文本、与全库的最近条目(含宽松阈值下的分);
3) 输出按"类"统计的清单, 供逐类目视复核。
"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
keep = json.load(open(os.path.join(B, 'review', 'dense2_dialogue.json'), encoding='utf-8'))


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def score(a, b):
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return min(sum(1 for ch in a if ch in sb) / len(a), sum(1 for ch in b if ch in sa) / len(b))


lib = []
for fn in sorted(os.listdir(CLEAN)):
    if fn.endswith('.json'):
        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
            t = cn(e.get('text'))
            if t:
                lib.append((fn[1:4], e['timestamp'], t))

# 聚类
clusters = []
for c in sorted(keep, key=lambda x: (x['ep'], x['sec'])):
    n = cn(c['text'])
    for cl in clusters:
        if score(n, cl['rep']) >= 0.7:
            cl['items'].append(c)
            if len(n) > len(cl['rep']):
                cl['rep'] = n
            break
    else:
        clusters.append({'rep': n, 'items': [c]})

print(f'765 条疑似台词 -> {len(clusters)} 类')
rows = []
for cl in clusters:
    best, arg = 0.0, None
    for ep, ts, lt in lib:
        if abs(len(lt) - len(cl['rep'])) > 10:
            continue
        s = score(cl['rep'], lt)
        if s > best:
            best, arg = s, (ep, ts, lt)
    rows.append((cl, best, arg))
rows.sort(key=lambda x: -x[1])

lines = [f'疑似台词聚类: {len(clusters)} 类(原始 765 条)', '']
lines.append('== 与库最近但仍 <0.7 的(优先复核, 分数越低越可能真缺) ==')
for cl, best, arg in rows[:120]:
    eps = sorted({i['ep'] for i in cl['items']})
    ts = [i['t'] for i in cl['items']][:4]
    lines.append(f"  [{cl['rep']}] ×{len(cl['items'])} 集={eps[:4]} 位置={ts}  最近库={arg} 分={best:.2f}")
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'dense2_clusters.txt'), 'w', encoding='utf-8').write(txt)
json.dump([{'rep': cl['rep'], 'n': len(cl['items']),
            'items': [{'ep': i['ep'], 't': i['t'], 'text': i['text']} for i in cl['items']],
            'best_score': round(best, 2), 'best_lib': arg} for cl, best, arg in rows],
          open(os.path.join(B, 'review', 'dense2_clusters.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(txt[:6000])
