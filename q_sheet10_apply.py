# -*- coding: utf-8 -*-
"""q_sheet10_apply.py — 应用"字幕带原尺寸对照表"逐条看图后的判定(16 张表 / 156 条)。

对照表 review/q_sheet10_*.jpg 只贴字幕带(960x540 帧的 y436~504)并保持原尺寸, 因此字幕可读 ——
这是本轮唯一能看到"用户实际看到的那句话原文"的方式。
(整帧缩略图方案失败过: 1560x3750 的表被读图工具缩到 516x1240, 字幕只剩 ~5px。)

结论: 156 条里绝大多数**库文本是对的**(此前判"帧上是另一句"多为识别噪声),
真正要动的只有下面这些。

用法: python q_sheet10_apply.py [--dry]
"""
import json
import os
import shutil
import sys
import time

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle_clean')

# 帧上清楚显示完整句, 旧文本是它的真子序列或明显截断 —— 方向可靠
FIX = [
    ('P08', '16m52s', '罗索奥特曼烈', '罗索奥特曼烈火形态'),
    ('P10', '16m32s', '减分', '减10分'),
    ('P14', '0m12s', '总', '总觉得上一集的爸爸有点奇怪啊'),
    ('P20', '6m51s', '之前我就觉得她不是个普通的女孩子理', '之前我就觉得她不是个普通的女孩子'),
    ('P25', '23m36s', '那我也走', '那我也走了'),
    ('P16', '5m21s', '.3我赶了个装置出来', '我赶了个装置出来'),
    # 库文本本身是乱码, 帧上是完整通顺的一句
    ('P11', '10m10s', '中十', '打败怪兽时的必杀技超帅'),
    ('P12', '4m51s', '会这样心', '怎么会这样'),
    ('P16', '15m12s', '海巢海话', '活海哥勇海哥'),
    # P25 片尾: 台词与演职员表叠在同一帧, 库文本把两者混在了一起 —— 只保留台词部分
    ('P25', '22m28s', '小神野黄爸爸面川忠久', '爸爸'),
    ('P25', '22m35s', '你没事吧小林裕佐大良太', '你没事吧'),
    ('P25', '22m36s', '你没事吧林慧', '你没事吧'),
    ('P25', '22m37s', '王林你没事吧', '你没事吧'),
    ('P25', '22m38s', '真是的江川千恵子黑本道', '真是的'),
    ('P25', '22m39s', '真是的冷林', '真是的'),
    ('P25', '22m40s', '真是的林', '真是的'),
    ('P25', '23m34s', '开工干活吧原田笙太', '开工干活吧'),
]

# 帧上是乱码/无字幕, 库文本本身也无意义, 或与相邻条目重复的残句
DELETE = [
    ('P05', '7m06s', '上为音力世\n品克\n中加市\n标说'),
    ('P06', '17m26s', '上七'),
    ('P07', '11m22s', '爱司厂'),
    ('P09', '17m18s', '号會'),
    ('P12', '16m12s', '心出'),
    ('P14', '21m41s', '上上'),
    ('P18', '0m58s', '一路'),
    ('P25', '23m47s', '监督 武居正能'),
    ('P25', '23m53s', '宁东京電通'),
]


def main():
    dry = '--dry' in sys.argv
    by_ep = {}
    for f in sorted(os.listdir(CLEAN)):
        if f.endswith('.json') and f.startswith('['):
            by_ep[f[1:4]] = f
    n_fix = n_del = 0
    for ep, fn in sorted(by_ep.items()):
        data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
        keep, changed = [], False
        for e in data:
            ts, txt = e.get('timestamp'), e.get('text', '')
            hit = next((x for x in FIX if x[0] == ep and x[1] == ts and x[2] == txt), None)
            if hit:
                e['text'] = hit[3]
                n_fix += 1
                changed = True
                print(f"  改 {ep} {ts}: [{hit[2]}] -> [{hit[3]}]")
                keep.append(e)
                continue
            if any(x[0] == ep and x[1] == ts and x[2] == txt for x in DELETE):
                n_del += 1
                changed = True
                print(f"  删 {ep} {ts}: [{txt[:24]}]")
                continue
            keep.append(e)
        if changed and not dry:
            shutil.copy2(os.path.join(CLEAN, fn), os.path.join(CLEAN, fn + '.bak_s10'))
            json.dump(keep, open(os.path.join(CLEAN, fn), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
    print(f'\n修正 {n_fix} 条 / 删除 {n_del} 条{"（预演）" if dry else ""}')
    json.dump({'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'dry': dry,
               'n_fix': n_fix, 'n_del': n_del, 'fix': FIX, 'delete': DELETE},
              open(os.path.join(REVIEW, 'q_sheet10_apply.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
