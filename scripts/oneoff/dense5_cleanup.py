# -*- coding: utf-8 -*-
"""清理第四轮混入的非台词条目, 并修正一处带杂字前缀的文本。"""
import json
import os
import sys

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
DEL = ['人7第3集欢迎来到爱染科技', '何百回何干回何万回', '何千回何万回何百回', '何百回何千回1何万回',
       '堅結', '右強羽物語', '何万回一何百回何回', '羽物語強', '起喊快乐', '繫重未来入', '信抜',
       '家族想繋物語', '決揺', '見奇跡0叫', '愛情力友情力交差', '家族薬物語', '想物語家族',
       '想繫物語家族', '見奇跡04中', '第22集异次元妈妈', '君笑顔希望', '君勇気未来', '僕声君声',
       '守全部', '重合行', '乗越戦', '強羽物語', '決絆諦', '繫重未来', '決明日諦', '瞬間起奇跡嘘',
       '星明日', '信先輝']
FIX = [('P18', '見見驚感動那种惊讶和感动', '那种惊讶和感动')]

apply = '--apply' in sys.argv
tot_del = tot_fix = 0
for fn in sorted(os.listdir(CLEAN)):
    if not fn.endswith('.json'):
        continue
    p = os.path.join(CLEAN, fn)
    data = json.load(open(p, encoding='utf-8'))
    n0 = len(data)
    data = [e for e in data if (e.get('text') or '').strip() not in DEL]
    d = n0 - len(data)
    f = 0
    for ep, old, new in FIX:
        if not fn.startswith(f'[{ep}]'):
            continue
        for e in data:
            if (e.get('text') or '').strip() == old:
                e['text'] = new
                f += 1
    if d or f:
        print(f'  {fn[:5]}: 删除 {d}, 修正 {f}')
        tot_del += d
        tot_fix += f
        if apply:
            json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'共删除 {tot_del}, 修正 {tot_fix}' + ('(已落盘)' if apply else '(预演)'))
