# _make_snapshot.py — 把 Web/ 的单页应用打包成"双击即看"的单文件快照
# 用途: 给设计改动留一个不依赖 git、不依赖服务器的回退参照物
# 用法: python _make_snapshot.py <输出路径>
# 注意: 快照里的 frames/ 与 assets/ 仍是相对路径, 所以它要放在 Web/ 下(或与之同级)才能显示图片
#
# 坑: 不能用 re.sub 做替换 —— 替换串里的 \d 之类会被当成正则转义而报错(JS 里全是反斜杠)。
#     这里用 str.replace 做字面量替换, 并且显式吃掉 ?v=NN 版本号。
import os
import re
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Web')
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, '_snapshot.html')

html = open(os.path.join(BASE, 'index.html'), encoding='utf-8').read()

# 样式表: 把 href="style.css?v=NN" 整段换成内联 <style>
css_ref = re.search(r'<link rel="stylesheet" href="style\.css[^"]*">', html)
if not css_ref:
    sys.exit('未找到 style.css 的外链, index.html 结构可能变了')
css = open(os.path.join(BASE, 'style.css'), encoding='utf-8').read()
html = html.replace(css_ref.group(0), '<style>\n' + css + '\n</style>')

# 脚本: 同理
js_ref = re.search(r'<script src="script\.js[^"]*"></script>', html)
if not js_ref:
    sys.exit('未找到 script.js 的外链, index.html 结构可能变了')
js = open(os.path.join(BASE, 'script.js'), encoding='utf-8').read()
html = html.replace(js_ref.group(0), '<script>\n' + js + '\n</script>')

open(out, 'w', encoding='utf-8').write(html)
print(f'快照已写出: {out}  ({os.path.getsize(out) / 1024:.1f} KB)')
print('提示: 放在 Web/ 目录下打开, 图片才能按相对路径找到')
