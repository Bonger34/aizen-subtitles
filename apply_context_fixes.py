# -*- coding: utf-8 -*-
"""apply_context_fixes.py — 按密集序列修复前后句（每条真句独立入库）

决定表（依据 review/context_dense.json 序列）：
  每条 TARGET：set_text（该 ts 应为何句）+ append_text（应补插的相邻真句）
  库现状检查 + 更新 + 邻接去重。
"""
import json
import os

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')

# (ep, [(ts, text, 模式)])  模式: 'set'=该ts覆盖为text, 'append'=补插text条目(ts)
FIX = {
    'P19': [('6m13s', '又是她召唤的吧', 'update'),   # 已回滚=A ✓
            ('6m16s', '不是我干的', 'update'),
            ('6m19s', '有人入侵了系统', 'append'),
            ('6m21s', '控制了达令', 'append')],
    'P01': [('5m21s', '我回来了', 'update'),
            ('5m22s', '你回来啦', 'append'),
            ('24m22s', '我们得打败它才行', 'update')],
    'P02': [('4m59s', '那不是挺好的嘛', 'update'),
            ('5m00s', '我很喜欢啊很不错啊', 'append'),
            ('6m52s', '真是厉害', 'update'),
            ('6m54s', '你真是身手不凡呢', 'append'),
            ('19m19s', '勇海要到时间了', 'update'),
            ('19m21s', '用你的技能把那家伙丢到空中去', 'append')],
    'P08': [('16m31s', '泰罗奥特曼', 'update'),
            ('16m32s', '银河奥特曼', 'append')],
    'P16': [('10m08s', '一定不会错的朝阳就在这附近', 'update')],
    'P20': [('4m39s', '注意后面有客人', 'update'),
            ('4m40s', '有客人来了', 'append')],
    'P22': [('4m55s', '小澪', 'append'),
            ('4m56s', '小潮', 'update'),
            ('17m22s', '泰罗奥特曼', 'update'),
            ('17m23s', '银河奥特曼', 'append')],
}


def main():
    total = {'update': 0, 'append': 0, 'skip': 0}
    log = []
    for ep, items in FIX.items():
        fs = [f for f in os.listdir(CLEAN_DIR) if f.startswith(f'[{ep}]') and f.endswith('.json')]
        if not fs:
            continue
        path = os.path.join(CLEAN_DIR, fs[0])
        data = json.load(open(path, encoding='utf-8'))
        exist = {r.get('timestamp'): r for r in data}
        for ts, text, mode in items:
            if mode == 'update':
                if ts in exist:
                    if exist[ts]['text'] != text:
                        log.append({'ep': ep, 'ts': ts, 'from': exist[ts]['text'][:26],
                                    'to': text})
                        exist[ts]['text'] = text
                        total['update'] += 1
                    else:
                        total['skip'] += 1
                else:
                    data.append({'timestamp': ts, 'text': text, 'similarity': 0.0})
                    exist[ts] = data[-1]
                    log.append({'ep': ep, 'ts': ts, 'from': '(无)', 'to': text})
                    total['update'] += 1
            else:  # append
                # 避免与已有条目重复（同名文本出现在 ±4s 内则跳过）
                dup = any(abs(int(r.get('timestamp', '0m0s').rstrip('s').split('m')[0]) * 60
                              + int(r.get('timestamp', '0m0s').split('m')[1].rstrip('s'))
                              - (int(ts.rstrip('s').split('m')[0]) * 60
                                 + int(ts.split('m')[1].rstrip('s'))) ) <= 4
                          and r.get('text', '') == text for r in data)
                if dup:
                    total['skip'] += 1
                    continue
                data.append({'timestamp': ts, 'text': text, 'similarity': 0.0})
                log.append({'ep': ep, 'ts': ts, 'from': '(补)', 'to': text})
                total['append'] += 1
        json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('结果:', total)
    with open(os.path.join(BASE, 'review', 'context_fixes_applied.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(log, fh, ensure_ascii=False, indent=1)
    for x in log:
        print(f"  {x['ep']} {x['ts']}: {x['from'][:16]} → {x['to'][:16]}")


if __name__ == '__main__':
    main()
