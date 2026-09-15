# -*- coding: utf-8 -*-
"""q_review9_apply.py — 处理第 4 轮残留清单里的两类问题(逐条人工看过 586 条上下文后)。

一、删除: 上一步 q_outscope_delete.py 漏掉的带外内容 —— 这些条目的文本本身没有姓名用字、
    也没有"版权"字样, 所以没被那条规则抓到, 但逐条看上下文后完全可判:
      * 片尾演职员表的 OCR 碎片(東葛柏市城市 / 野出有抄 / 尚本坂开样波亮太 ...)
      * 下集预告/标题卡(第3集欢迎来 / 第集宿敌口 / 指日 / 白千 ...)
      * 画面上的日文(見見茶感動 / 熱感阿 / 山油十日汉十户 ...)
      * 新闻滚动条(住几七品工的山用 / 拜托了铭10售机专用 ...)
    判据 = 落在"片尾/预告区块的时间区间"内 **且** 文本不含任何台词虚词。
    留一道保险: 含 的了是我你他不在吗呢吧啊这那怎么什么 等虚词的, 或长度 >= 5 且含"得/也/要/就"
    的, 一律保留(宁可漏删)。

二、修正: 上下文一眼能定的错字(生目快乐->生日快乐、永晶->水晶、恤->T恤 ...)。

用法: python q_review9_apply.py [--dry]
输出: review/q_review9_apply.json
"""
import json
import os
import re
import shutil
import sys
import time
from collections import Counter

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle_clean')

# 片尾/预告/图形文字的区块(每集逐个看过上下文后确定); 区间内还要过"虚词保险"
GARBAGE_SPANS = {
    'P02': [('22m58s', '23m20s')],
    'P03': [('22m49s', '23m42s'), ('24m05s', '24m05s'), ('3m50s', '3m50s')],
    'P04': [('22m38s', '23m41s')],
    'P05': [('23m00s', '23m00s')],
    'P06': [('1m57s', '1m58s'), ('22m57s', '23m21s'), ('24m04s', '24m04s')],
    'P07': [('22m59s', '23m21s'), ('24m00s', '24m00s'), ('24m31s', '24m31s')],
    'P08': [('22m59s', '23m44s')],
    'P09': [('23m00s', '23m44s')],
    'P10': [('22m38s', '22m38s'), ('24m03s', '24m03s')],
    'P11': [('23m31s', '23m35s')],
    'P12': [('12m11s', '12m11s'), ('23m22s', '23m35s')],
    'P13': [('21m12s', '21m12s'), ('23m11s', '24m07s')],
    'P14': [('23m27s', '23m34s'), ('24m06s', '24m06s'), ('24m35s', '24m35s')],
    'P15': [('10m05s', '10m05s'), ('16m01s', '16m01s'), ('23m29s', '23m44s'),
            ('24m03s', '24m07s')],
    'P16': [('17m40s', '17m40s'), ('18m37s', '18m37s'), ('23m17s', '23m44s'),
            ('23m58s', '24m11s')],
    'P17': [('23m27s', '23m45s'), ('24m06s', '24m06s'), ('24m11s', '24m11s')],
    'P18': [('2m55s', '3m15s'), ('7m05s', '7m38s'), ('22m13s', '22m15s'),
            ('23m30s', '23m34s'), ('23m54s', '23m54s'), ('24m07s', '24m13s')],
    'P19': [('22m53s', '22m53s'), ('23m31s', '23m32s'), ('24m00s', '24m10s'),
            ('5m59s', '6m02s')],
    'P20': [('18m35s', '18m35s'), ('21m22s', '21m22s'), ('21m39s', '21m39s'),
            ('23m30s', '23m31s'), ('24m01s', '24m26s')],
    'P21': [('19m42s', '19m42s'), ('22m56s', '22m56s'), ('23m35s', '23m39s'),
            ('24m06s', '24m12s')],
    'P22': [('23m21s', '23m34s'), ('23m59s', '24m32s'), ('4m51s', '4m59s')],
    'P23': [('22m56s', '22m56s'), ('23m29s', '23m29s'), ('23m46s', '23m47s'),
            ('24m00s', '24m05s')],
    'P24': [('23m56s', '23m56s'), ('24m02s', '24m04s'), ('8m06s', '8m06s')],
}
# P25 的片尾与台词叠在一起, 不能按区间删 —— 逐条列出(全部看过上下文)
P25_DELETE = ['21m02s', '21m03s', '21m05s', '21m13s', '21m23s', '21m25s', '21m26s',
              '21m33s', '21m35s', '21m39s', '21m54s', '22m18s', '22m19s', '22m20s',
              '22m24s', '22m30s', '22m31s', '22m54s', '22m57s', '22m59s', '23m00s',
              '23m01s', '23m02s', '23m03s', '23m04s', '23m05s', '23m06s', '23m07s',
              '23m09s', '23m10s', '23m11s', '23m12s', '23m13s', '23m14s', '23m15s',
              '23m16s', '23m17s', '23m18s', '23m19s', '23m20s', '23m21s', '23m22s',
              '23m23s', '23m25s', '23m27s', '23m39s', '23m40s', '23m41s', '23m42s',
              '23m43s', '23m44s', '23m45s', '23m46s', '23m48s']

FUNC = set('的了是我你他她它们不吗呢吧啊这那怎么办什么怎么还会就要能可以') \
    - {'有', '下', '一', '二', '三', '上'}

# 上下文一眼能定的错字修正
FIXES = [
    ('P03', '5m20s', '那个我是凑活澪的', '那个我是凑澪的'),
    ('P03', '6m52s', '以改革新的生活方式为自标的', '以改革新的生活方式为目标的'),
    ('P04', '3m19s', '这么久以来谢谢备位了', '这么久以来谢谢各位了'),
    ('P05', '9m26s', '风鸣不过是谁埋在那里的呢', '不过是谁埋在那里的呢'),
    ('P05', '24m21s', '我们不会认输的勺小牧姐', '我们不会认输的小牧姐'),
    ('P06', '15m31s', '吃就你了', '就你了'),
    ('P08', '0m34s', '惠理奈生目快乐这是给你的礼物', '惠理奈生日快乐这是给你的礼物'),
    ('P08', '0m43s', '你生自是什么时候来着', '你生日是什么时候来着'),
    ('P08', '10m47s', '这旬话以前已经有人说过了', '这句话以前已经有人说过了'),
    ('P08', '16m53s', '罗索奥特烈火形态', '罗索奥特曼烈火形态'),
    ('P09', '16m39s', '我一眨眼就超过你们门了哟', '我一眨眼就超过你们了哟'),
    ('P10', '12m37s', '这样吧我有有一个提案', '这样吧我有一个提案'),
    ('P10', '20m32s', '一真是悲哀', '真是悲哀'),
    ('P11', '0m29s', '哥哥你好帅呀心', '哥哥你好帅呀'),
    ('P11', '6m16s', '卡太好了', '太好了'),
    ('P12', '15m01s', '无论如何都必须打败它役', '无论如何都必须打败它'),
    ('P12', '21m48s', '麻利点雨', '麻利点'),
    ('P12', '24m31s', '党妹之间无秘密', '兄妹之间无秘密'),
    ('P13', '16m14s', '毕竟竟小澪很怕羞', '毕竟小澪很怕羞'),
    ('P14', '9m47s', '他只是借着恤开玩笑的', '他只是借着T恤开玩笑的'),
    ('P14', '9m48s', '他只是借着恤开玩笑的', '他只是借着T恤开玩笑的'),
    ('P15', '11m22s', '就你了罗布水晶第', '就你了罗布水晶'),
    ('P16', '5m14s', '还有叶草', '还有四叶草'),
    ('P16', '23m52s', '是的今天的永晶是这个', '是的今天的水晶是这个'),
    ('P16', '24m29s', '卞一集罗布奥特曼', '下一集罗布奥特曼'),
    ('P17', '6m35s', '心回事', '怎么回事'),
    ('P18', '1m30s', '之后', '广告之后'),
    ('P18', '6m26s', '这些可都是我们店里最棒的恤了', '这些可都是我们店里最棒的T恤了'),
    ('P18', '16m23s', '不管任何时候都要继续制作恤', '不管任何时候都要继续制作T恤'),
    ('P18', '23m54s', '是的今天的永晶是这个', '是的今天的水晶是这个'),
    ('P20', '6m54s', '剑就是小剑', '小剑就是小剑'),
    ('P21', '4m32s', '你看这款恤卖得可好了', '你看这款T恤卖得可好了'),
    ('P21', '17m22s', '就你罗布水晶', '就你了罗布水晶'),
    ('P22', '17m20s', '就你了罗冰晶', '就你了罗布水晶'),
    ('P22', '23m52s', '是的今天的水晶是这个技', '是的今天的水晶是这个'),
    ('P23', '1m38s', '明百', '明白'),
    ('P24', '10m10s', '没有这座城市哪来的之家', '没有这座城市哪来的M之家'),
    ('P24', '11m43s', '澳特战士', '奥特战士'),
    ('P11', '10m04s', '当然是新的那十他看起来好像更厉害一\n\n业能县新始那',
     '他看起来好像更厉害一些'),
]
# 与相邻条目重复的残句(上半句/下半句被拆成两条) —— 删除
DUPS = [('P09', '11m04s', '下次要阿'), ('P13', '19m59s', '这东西到底是什'),
        ('P14', '5m15s', '威廉莎士比亚当'), ('P18', '9m26s', '奥特战士的爸爸哦'),
        ('P15', '4m23s', '个个个'), ('P04', '14m20s', '心'),
        ('P19', '0m08s', '才生'), ('P18', '1m03s', '助?')]

# 含虚词所以被"虚词保险"放过了, 但逐条看上下文后确认仍是乱码的 —— 显式删掉
EXTRA_DELETE = [('P03', '22m49s'), ('P03', '23m01s'), ('P05', '23m00s'),
                ('P16', '24m03s'), ('P16', '24m04s'), ('P16', '24m07s'),
                ('P18', '2m55s'), ('P18', '2m58s'), ('P18', '3m06s'), ('P18', '3m08s'),
                ('P18', '3m09s'), ('P18', '3m10s'), ('P18', '3m12s'), ('P18', '3m14s'),
                ('P18', '3m15s'), ('P18', '22m15s'),
                ('P20', '21m22s'), ('P20', '24m12s'), ('P20', '24m22s')]


def ts2sec(t):
    m = re.match(r'(\d+)m(\d+)s', t)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else -1


def main():
    dry = '--dry' in sys.argv
    # 结构性保险: 凡出现在历次"已应用修正"清单里的条目不删 —— 它们已被人工确认过是台词。
    # (踩过: P18 7m15s「凑潮50岁」、P25 23m43s「路上小心」都因为不含虚词被区间规则误删)
    protect = set()
    for fn in ('q_apply_result.json', 'q_apply2_result.json'):
        p = os.path.join(REVIEW, fn)
        if os.path.exists(p):
            for a in json.load(open(p, encoding='utf-8')).get('applied', []):
                protect.add((a['ep'], a['ts']))
    p = os.path.join(REVIEW, 'q_manual_verdicts.json')
    if os.path.exists(p):
        for a in json.load(open(p, encoding='utf-8')).get('frame_apply', []):
            protect.add((a['ep'], a['ts']))
    print(f'受保护(历次修正过)的条目 {len(protect)} 条')

    by_ep = {}
    for f in sorted(os.listdir(CLEAN)):
        if f.endswith('.json') and re.match(r'^\[P\d+\]', f):
            by_ep[re.search(r'\[(P\d+)\]', f).group(1)] = f

    dels, fixes, log = [], [], []
    for ep, fn in by_ep.items():
        data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
        spans = [(ts2sec(a), ts2sec(b)) for a, b in GARBAGE_SPANS.get(ep, [])]
        keep, changed = [], False
        for e in data:
            ts, txt = e.get('timestamp'), e.get('text', '')
            sec = ts2sec(ts)
            kill = False
            if (ep, ts) in protect:
                kill = False
            elif ep == 'P25' and ts in P25_DELETE:
                kill = True
            elif any(a <= sec <= b for a, b in spans):
                # 虚词保险: 含台词虚词的一律保留(宁可漏删)
                if not (set(txt) & FUNC):
                    kill = True
            if not kill and any(ep == d[0] and ts == d[1] and txt == d[2] for d in DUPS):
                kill = True
            if not kill and (ep, ts) in EXTRA_DELETE:
                kill = True
            if kill:
                dels.append({'ep': ep, 'ts': ts, 'old': txt})
                changed = True
                continue
            for fep, fts, old, new in FIXES:
                if ep == fep and ts == fts and txt == old:
                    e['text'] = new
                    fixes.append({'ep': ep, 'ts': ts, 'from': old, 'to': new})
                    changed = True
            keep.append(e)
        if changed and not dry:
            shutil.copy2(os.path.join(CLEAN, fn), os.path.join(CLEAN, fn + '.bak_r9'))
            json.dump(keep, open(os.path.join(CLEAN, fn), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
        log.append(f'{ep}: 删 {len(data) - len(keep) if not any(f[0] == ep for f in FIXES) else sum(1 for d in dels if d["ep"] == ep)}')

    print(f'删除 {len(dels)} 条 / 修正 {len(fixes)} 条{"（预演）" if dry else ""}')
    print('按集删除:', dict(Counter(d['ep'] for d in dels)))
    print('\n保留但值得再看一眼的(区间内因含虚词而保留的):')
    for ep, spans in GARBAGE_SPANS.items():
        data = json.load(open(os.path.join(CLEAN, by_ep[ep]), encoding='utf-8'))
        for e in data:
            sec = ts2sec(e.get('timestamp'))
            if any(a <= sec <= b for a, b in [(ts2sec(a), ts2sec(b)) for a, b in spans]):
                if set(e.get('text', '')) & FUNC:
                    print(f"   {ep} {e['timestamp']:>7s} [{e['text'][:34]}]")
    out = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'dry': dry,
           'n_del': len(dels), 'n_fix': len(fixes), 'deleted': dels, 'fixed': fixes}
    json.dump(out, open(os.path.join(REVIEW, 'q_review9_apply.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'\n输出: review/q_review9_apply.json')


if __name__ == '__main__':
    main()
