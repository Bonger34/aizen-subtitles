# -*- coding: utf-8 -*-
"""q_sheet11_apply.py — 应用第二批"字幕带原尺寸对照表"逐条看图后的判定(14 张表 / 136 条)。

对照表 review/q_sheet11_*.jpg。136 条里绝大多数库文本正确; 下面这些是看图后要动的。

其中 P05 9m26s 是**撤销我自己的错误修改**: 上一轮我把「风鸣不过是谁埋在那里的呢」当成噪声
去掉了开头两字, 而画面明确写着「风鸣 不过 是谁埋在那里的呢」。

用法: python q_sheet11_apply.py [--dry]
"""
import json
import os
import shutil
import sys
import time

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle_clean')

FIX = [
    ('P02', '8m33s', '这位客人美', '这位客人'),                       # 去尾部"美"
    ('P03', '4m56s', '波刚平一飞冲天', '一波刚平一飞冲天'),            # 补首字"一"
    ('P05', '9m26s', '不过是谁埋在那里的呢', '风鸣不过是谁埋在那里的呢'),  # 撤销上一轮的错误删除
    ('P08', '9m54s', '爱染先生希望我们把恤送到这里去', '爱染先生希望我们把T恤送到这里去'),
    ('P08', '10m09s', '好的吧二', '好的吧'),                          # 去尾部"二"
    ('P08', '10m10s', '好韵吧', '好的吧'),                            # 韵->的
    ('P08', '11m23s', '已经做成发送到你们的邮箱了', '已经做成PDF发送到你们的邮箱了'),
    ('P08', '12m05s', '我已经被关在这具身体里年之久了', '我已经被关在这具身体里15年之久了'),
    ('P11', '24m27s', '活海哥建海', '活海哥勇海哥'),
    ('P13', '4m02s', '一切就都不一样了真', '一切就都不一样了'),        # 去尾部"真"
    ('P15', '3m08s', '它被束缚在了绫香市的市中', '它被束缚在了绫香市的市中心'),
    ('P18', '24m21s', '即将发动计划', '即将发动AZ计划'),
    ('P20', '10m46s', '级警戒', '4级警戒'),
    ('P20', '12m54s', '骗人了', '少骗人了'),
    ('P21', '16m43s', '我说谎了不', '不我说谎了'),                    # 画面为"不 我说谎了"
    ('P22', '1m03s', '不好意思小', '不好意思'),                       # 去尾部"小"
    ('P23', '3m34s', '还有秒鲁格赛特将抵达', '还有3秒鲁格赛特将抵达'),
    # P25 片尾: 台词与演职员表叠在同一帧, 只保留台词
    ('P25', '22m25s', '你怎么了爸爸車盛川一男', '你怎么了爸爸'),
    ('P25', '22m26s', '怎么了小酒井介小', '怎么了'),
    ('P25', '22m27s', '怎么了小神野貴嗣心', '怎么了'),
    ('P25', '22m32s', '爸爸就像奥特战士一样啊及川将人小船有紀子', '爸爸就像奥特战士一样啊'),
    ('P25', '22m34s', '爸爸就像奥特战士一样啊勝又拓海', '爸爸就像奥特战士一样啊'),
]


def main():
    dry = '--dry' in sys.argv
    by_ep = {}
    for f in sorted(os.listdir(CLEAN)):
        if f.endswith('.json') and f.startswith('['):
            by_ep[f[1:4]] = f
    n, miss = 0, []
    todo = {}
    for ep, ts, old, new in FIX:
        todo.setdefault(ep, {})[ts] = (old, new)
    for ep, fn in sorted(by_ep.items()):
        if ep not in todo:
            continue
        data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
        changed = False
        for e in data:
            ts = e.get('timestamp')
            if ts in todo[ep]:
                old, new = todo[ep][ts]
                if e.get('text') == old:
                    e['text'] = new
                    n += 1
                    changed = True
                    print(f"  改 {ep} {ts}: [{old}] -> [{new}]")
                else:
                    miss.append({'ep': ep, 'ts': ts, 'expect': old, 'lib': e.get('text')})
        if changed and not dry:
            shutil.copy2(os.path.join(CLEAN, fn), os.path.join(CLEAN, fn + '.bak_s11'))
            json.dump(data, open(os.path.join(CLEAN, fn), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
    print(f'\n修正 {n} 条{"（预演）" if dry else ""} / 对不上 {len(miss)} 条')
    for m in miss:
        print('  对不上:', m)
    json.dump({'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'dry': dry, 'n': n,
               'fix': FIX, 'mismatch': miss},
              open(os.path.join(REVIEW, 'q_sheet11_apply.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
