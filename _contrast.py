# _contrast.py — 前端评审: 按 WCAG 2.1 相对亮度公式算正文/次级文本对比度
# 临时脚本, 跑完可删
import re


def lum(hexstr):
    h = hexstr.lstrip('#')
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


css = open('docs/style.css', encoding='utf-8').read()
vars_ = dict(re.findall(r'--([a-z-]+):\s*(#[0-9A-Fa-f]{6})', css))

# body 背景是渐变, 取三个停靠色 + 卡片玻璃底层作为近似背景
bgs = {
    'body #10152A': '#10152A',
    'body --deep #1A2236': vars_['deep'],
    'body #0C1220': '#0C1220',
    '卡片底(玻璃 .72 叠深空)': '#141A2A',
}
fgs = ['ink', 'ink-soft', 'ink-faint', 'white', 'gold', 'blush', 'violet-soft']

print('前景 \\ 背景'.ljust(22) + ''.join(k.ljust(24) for k in bgs))
for f in fgs:
    row = f'{f} {vars_.get(f)}'
    for k, b in bgs.items():
        r = ratio(vars_[f], b)
        mark = 'OK ' if r >= 4.5 else ('AA大字' if r >= 3.0 else '不足 ')
        row += f'{mark}{r:5.2f}'.ljust(24)
    print(row)

print()
print('参考: WCAG 2.1 AA 正文 4.5:1 / 大字(>=18.66px 粗体或 >=24px) 3.0:1')
print()
print('页面里用到 --ink-soft / --ink-faint 的正文型元素:')
for m in re.finditer(r'([^{}]+)\{([^}]*)\}', css):
    sel, body = m.group(1).strip().replace('\n', ' '), m.group(2)
    if re.search(r'color:\s*var\(--ink-(soft|faint)\)', body):
        size = re.search(r'font-size:\s*([^;]+);', body)
        print('   ', sel[:60].ljust(62), 'font-size:', size.group(1).strip() if size else '(继承 1.6rem?)')
