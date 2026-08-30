# -*- coding: utf-8 -*-
"""fix_ascii_revert.py — 修正 merge 阶段 ASCII 边段清理的误伤/残留

逐条人工裁决（基于会话中打印的 [清] 记录）：
  P09 5m02s 「简称SSP」的 SSP 存疑 → 回退 VL 原始输出
  P10 6m04s  Schallplatt 为画面德语词 → 保持清理（无需操作）
  P10 11m48s 「₄谁会…」残留下标 → 整清为「谁会去你的公司工作」
  P15 5m18s  「GPS」为真实台词专有名词 → 回退
  P20 7m13s  「NASA」为真实台词专有名词 → 回退
  P22 9m22s  「(」残留括号 → 清为「追是追出来了」
按文本匹配（ts 已被校准改动，不能按 ts 定位）
"""
import json
import os

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')

FIXES = [
    ('简称', '简称SSP'),
    ('₄谁会去你的公司工作', '谁会去你的公司工作'),
    ('我在用朝阳手机里的', '我在用朝阳手机里的GPS'),
    ('SA和国立天文台等各国机构', 'NASA和国立天文台等各国机构'),
    ('追是追出来了(', '追是追出来了'),
]


def main():
    n = 0
    for old, new in FIXES:
        hits = []
        for fn in sorted(os.listdir(CLEAN_DIR)):
            if not fn.endswith('.json'):
                continue
            path = os.path.join(CLEAN_DIR, fn)
            data = json.load(open(path, encoding='utf-8'))
            for r in data:
                if r.get('text', '') == old:
                    hits.append((fn[:5], r.get('timestamp')))
        if len(hits) == 1:
            for fn in sorted(os.listdir(CLEAN_DIR)):
                if not fn.endswith('.json'):
                    continue
                path = os.path.join(CLEAN_DIR, fn)
                data = json.load(open(path, encoding='utf-8'))
                for r in data:
                    if r.get('text', '') == old:
                        print(f'  [修] {fn[:5]} {r.get("timestamp")} 「{old}」→「{new}」')
                        r['text'] = new
                        json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                        n += 1
                        break
                else:
                    continue
                break
        elif not hits:
            print(f'  [无] 未找到「{old}」')
        else:
            print(f'  [多] 「{old}」有 {len(hits)} 条: {hits}，跳过（需人工确认）')
    print(f'\n修正 {n} 条')


if __name__ == '__main__':
    main()
