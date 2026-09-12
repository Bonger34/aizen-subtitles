# -*- coding: utf-8 -*-
"""密集扫描候选的后处理: 按"只算台词"的口径过滤, 输出真候选清单。

排除:
  1. 版权声明卡 / 标题卡(正则命中)
  2. 跨集重复文案(同一文本在 >=3 集出现 -> 片头片尾歌词、固定字幕)
  3. 噪声(中文 <2 字, 或数字占比过高)
  4. 片头/片尾窗内的非中文文本(0m45s-2m45s 与 22m20s-23m50s 的日文歌词)
其余为疑似台词, 输出供目视复核。
"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
OUTD = os.path.join(B, 'review', 'dense2')
RES = os.path.join(B, 'review', 'dense2_dialogue.txt')

COPY = re.compile(r'版权|新创华|文化发展|中国大陆|上海新|株式会社|製作|制作')
KANA = re.compile(r'[\u3040-\u30ff]')
JPNWORD = ('僕', '君', '絆', '諦', '未来', '絶対', '何百回', '何千回', '何万回', '乗越', '羽', '物語',
           '希望', '勇気', '笑顔', '守', '声', '離', '結', '堅', '強', '重', '行', '戦')


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff]', '', s or '')


def digits(s):
    d = re.sub(r'[^0-9]', '', s or '')
    return len(d) / max(1, len(s or ''))


files = sorted(f for f in os.listdir(OUTD) if f.endswith('.json'))
allc = []
for f in files:
    d = json.load(open(os.path.join(OUTD, f), encoding='utf-8'))
    for c in d['cands']:
        c['ep'] = d['ep']
        allc.append(c)
print(f'已扫描 {len(files)} 集, 候选合计 {len(allc)}')

dup = collections.Counter(cn(c['text']) for c in allc if len(cn(c['text'])) >= 3)

tally = collections.Counter()
keep = []
for c in allc:
    t, s, n = c['text'], c['sec'], cn(c['text'])
    if COPY.search(t):
        k = '版权/制作卡'
    elif len(n) < 2 or digits(t) > 0.5:
        k = '噪声'
    elif dup.get(n, 0) >= 3:
        k = '跨集重复(歌词/固定字幕)'
    elif (45 <= s <= 165 or 1340 <= s <= 1430) and (KANA.search(t) or sum(1 for w in JPNWORD if w in t) >= 1):
        k = '片头片尾(歌词)'
    else:
        k = '疑似台词'
        keep.append(c)
    tally[k] += 1
print('分类:')
for k, v in tally.most_common():
    print(f'   {k}: {v}')

lines = [f'密集扫描候选分类(已扫描 {len(files)} 集, 候选 {len(allc)})', '']
for k, v in tally.most_common():
    lines.append(f'  {k}: {v}')
lines.append(f'\n疑似台词 {len(keep)} 条:')
for c in sorted(keep, key=lambda x: (x['ep'], x['sec'])):
    lines.append(f"  {c['ep']} {c['t']:>7s}  [{c['text']}]  库匹配度={c['bef']}")
open(RES, 'w', encoding='utf-8').write('\n'.join(lines))
json.dump(keep, open(os.path.join(B, 'review', 'dense2_dialogue.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'写出 {RES}')
print('\n'.join(lines[:3]))
print('\n'.join(lines[-min(30, len(keep)) - 1:]))
