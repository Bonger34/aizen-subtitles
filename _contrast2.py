# _contrast2.py — 从真实渲染截图里取背景像素, 实算改动后的对比度
# 临时脚本, 跑完可删
import sys
from PIL import Image


def lum(rgb):
    f = [(c / 255) / 12.92 if (c / 255) <= 0.03928 else (((c / 255) + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


img = Image.open(sys.argv[1]).convert('RGB')
W, H = img.size
print(f'截图尺寸 {W}x{H}')

# 文案所在的两条带子, 取其中位数像素当背景(标题/统计在首屏, 结果卡在下方)
bands = {
    'hero 区(统计行所在带)': (570, 590),
    'hero 区(标题上方留白)': (150, 175),
    '页脚带': (H - 40, H - 20),
}
bgs = {}
for name, (y0, y1) in bands.items():
    y0, y1 = max(0, y0), min(H, y1)
    px = [img.getpixel((x, y)) for y in range(y0, y1) for x in range(0, W, 7)]
    px.sort(key=lambda p: sum(p))
    bgs[name] = px[len(px) // 2]          # 中位数 = 该带最常见的底色, 避开文字像素
    print(f'  {name}: 取到背景 rgb{bgs[name]}')

print()
print('改动后的前景色 vs 实取背景:')
checks = [
    ('--ink-faint #A9A3B2 (.result-meta / .random-string)', '#A9A3B2'),
    ('--violet-soft #8E7BD8 (.header-meta)', '#8E7BD8'),
    ('--ink-soft  #B8AFA3 (.hero-stats / .keyword-tag)', '#B8AFA3'),
]
for label, fg in checks:
    row = f'  {label:<52}'
    for name, bg in bgs.items():
        row += f' {name.split("(")[0].strip()}={ratio(hex2rgb(fg), bg):.2f}'
    print(row)

print()
print('改动前的前景色(对照):')
for label, fg in [('--ink-faint #7A7387 (旧)', '#7A7387'), ('--violet-soft #6E5FB8 (旧)', '#6E5FB8')]:
    row = f'  {label:<52}'
    for name, bg in bgs.items():
        row += f' {name.split("(")[0].strip()}={ratio(hex2rgb(fg), bg):.2f}'
    print(row)

print()
print('判定线: WCAG 2.1 AA 正文(<=18.66px 非粗体) 4.5:1 / 大字 3.0:1')
