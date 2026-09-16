# _review_probe.py — 前端评审用: 直接读库核对页面统计口径
# 临时脚本, 跑完可删
import gzip
import json
import collections

db = json.load(gzip.open('docs/subtitle_db', 'rt', encoding='utf-8'))
print('库条目数           =', len(db))
print('字段               =', sorted(db[0].keys()))
print('样本记录           =', json.dumps(db[0], ensure_ascii=False))

pre4 = collections.Counter(str(r['f'])[:4] for r in db)
print()
print("f[:4] 唯一值个数   =", len(pre4), "(页面用 eps = new Set(f.slice(0,4)) 算集数)")
for k, v in list(pre4.items())[:30]:
    print('   ', repr(k), v)

d_true = sum(1 for r in db if r.get('d'))
print()
print("d 真值条数         =", d_true, "(页面用它当'爱染诚登场')")

# 库文件名里第 4 个字符到底是什么
fourth = collections.Counter(str(r['f'])[3] for r in db)
print('第 4 个字符分布    =', dict(fourth))

# 文本里是否有 HTML 敏感字符(卡片用 innerHTML 拼接)
danger = [c for c in '<>&"\'' if any(c in str(r['x']) for r in db)]
print()
print('库文本含有的 HTML 敏感字符 =', danger or '无')
for c in danger:
    hit = [r for r in db if c in str(r['x'])][:3]
    print('   含', repr(c), '例:', [h['x'] for h in hit])
