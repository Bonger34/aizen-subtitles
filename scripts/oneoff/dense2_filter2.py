# -*- coding: utf-8 -*-
"""密集扫描候选后处理(定稿): 先用全库双向模糊匹配排除"其实已收录"的, 再按"只算台词"过滤。

步骤:
  1. 全库模糊匹配: 与任意库条目双向包含度 >= 0.7 -> 已收录(丢弃)
  2. 排除版权/制作卡、噪声(数字占比高或不足 2 字)
  3. 排除跨集重复文案(同文本 >=3 集出现 -> 片头片尾歌词/固定字幕)
  4. 余下为疑似台词, 逐条输出供目视复核
"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
OUTD = os.path.join(B, 'review', 'dense2')
RES = os.path.join(B, 'review', 'dense2_dialogue.txt')
COPY = re.compile(r'版权|新创华|文化发展|中国大陆|上海新')


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


lib = []
for fn in sorted(os.listdir(CLEAN)):
    if fn.endswith('.json'):
        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
            t = cn(e.get('text'))
            if t:
                lib.append((fn[1:4], e['timestamp'], t))
libsets = [(ep, ts, t, set(t)) for ep, ts, t in lib]
print('库条目', len(libsets))

allc = []
for f in sorted(os.listdir(OUTD)):
    if f.endswith('.json'):
        d = json.load(open(os.path.join(OUTD, f), encoding='utf-8'))
        for c in d['cands']:
            c['ep'] = d['ep']
            allc.append(c)
print('候选合计', len(allc))


def score(a, b):
    """双向包含度(取较小方向, 保守)。"""
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    ab = sum(1 for ch in a if ch in sb) / len(a)
    ba = sum(1 for ch in b if ch in sa) / len(b)
    return min(ab, ba)


dup = collections.Counter(cn(c['text']) for c in allc if len(cn(c['text'])) >= 3)
tally = collections.Counter()
keep = []
for c in allc:
    t, n = c['text'], cn(c['text'])
    if len(n) < 2 or (len(re.sub(r'[^0-9]', '', t)) / max(1, len(t))) > 0.5:
        tally['噪声'] += 1
        continue
    best, arg = 0.0, None
    for ep, ts, lt, _ in libsets:
        if abs(len(lt) - len(n)) > 8:
            continue
        s = score(n, lt)
        if s > best:
            best, arg = s, (ep, ts, lt)
            if best >= 0.95:
                break
    if best >= 0.7:
        tally['已收录(双向匹配)'] += 1
        continue
    if COPY.search(t):
        tally['版权/制作卡'] += 1
        continue
    if dup.get(n, 0) >= 3:
        tally['跨集重复(歌词/固定字幕)'] += 1
        continue
    tally['疑似台词'] += 1
    keep.append({**c, 'best_lib': arg, 'best_score': round(best, 2)})

print('分类:')
for k, v in tally.most_common():
    print(f'   {k}: {v}')
lines = [f'密集扫描候选后处理(候选 {len(allc)})', '']
for k, v in tally.most_common():
    lines.append(f'  {k}: {v}')
lines.append(f'\n疑似台词 {len(keep)} 条:')
for c in sorted(keep, key=lambda x: (x['ep'], x['sec'])):
    lines.append(f"  {c['ep']} {c['t']:>7s}  [{c['text']}]  最近库条目={c['best_lib']} 双向分={c['best_score']}")
open(RES, 'w', encoding='utf-8').write('\n'.join(lines))
json.dump(keep, open(os.path.join(B, 'review', 'dense2_dialogue.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'写出 {RES}; 疑似台词 {len(keep)} 条')
