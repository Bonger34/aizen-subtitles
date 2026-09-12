# -*- coding: utf-8 -*-
"""从 C/D 档(与库低相近)里筛出"像中文台词"的类: 要求含常见中文虚词, 且不是日文歌词式短串。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
rows = json.load(open(os.path.join(B, 'review', 'dense2_clusters.json'), encoding='utf-8'))
STOP = ['的', '了', '是', '我', '你', '他', '她', '不', '在', '吗', '吧', '呢', '啊', '什么',
        '怎么', '这', '那', '们', '和', '就', '都', '也', '还', '要', '会', '有', '没', '很',
        '好', '来', '去', '给', '把', '被', '让', '说', '看', '想', '知道', '一个', '这么', '那么']
LYRIC = ('何万回', '何百回', '何千回', '愛情', '友情', '交差', '繫', '未來', '未来', '絆', '諦',
         '絶対', '家族', '物語', '奇跡', '帰', '場所', '君', '僕', '笑顔', '笑顏', '勇気', '希望',
         '離', '結', '堅', '手手', '明日', '強', '羽', '声')

keep = []
for r in rows:
    t = r['rep']
    if r['best_score'] >= 0.4:
        continue
    if any(w in t for w in LYRIC):
        continue
    n_stop = sum(1 for w in STOP if w in t)
    if n_stop >= 1 and len(t) >= 3:
        keep.append((r, n_stop))

print(f'C/D 档 {sum(1 for r in rows if r["best_score"] < 0.4)} 类 -> 像中文台词 {len(keep)} 类')
lines = ['C/D 档中"像中文台词"的类(含中文虚词、排除歌词特征词):', '']
for r, ns in sorted(keep, key=lambda x: (x[0]['best_score'], -x[0]['n'])):
    loc = ' '.join(f"{i['ep']}{i['t']}" for i in r['items'][:5])
    lines.append(f"  [{r['rep']}] ×{r['n']}  {loc}   最近库={r['best_lib']}({r['best_score']}) 虚词数={ns}")
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'dense2_dialogue_cd.txt'), 'w', encoding='utf-8').write(txt)
print(txt[:7000])
