# _compare.py — 把两个版本的渲染图拼成一张并排对比图(左=当前主线, 右=分支新版)
# 用法: python _compare.py <左图> <右图> <输出> <左标签> <右标签>
import sys
from PIL import Image, ImageDraw

left_p, right_p, out, label_l, label_r = sys.argv[1:6]
L, R = Image.open(left_p).convert('RGB'), Image.open(right_p).convert('RGB')
# 统一高度, 宽度按比例缩放
h = max(L.height, R.height)
def fit(im):
    if im.height == h:
        return im
    w = round(im.width * h / im.height)
    return im.resize((w, h), Image.LANCZOS)
L, R = fit(L), fit(R)

BAR, GAP, PAD = 34, 14, 16
W = PAD + L.width + GAP + R.width + PAD
canvas = Image.new('RGB', (W, h + BAR + PAD * 2), (10, 13, 20))
d = ImageDraw.Draw(canvas)

d.rectangle([0, 0, PAD + L.width + GAP // 2, BAR], fill=(32, 38, 58))
d.rectangle([PAD + L.width + GAP // 2, 0, W, BAR], fill=(60, 44, 20))
d.text((PAD + 6, 11), label_l, fill=(230, 226, 216))
d.text((PAD + L.width + GAP + 6, 11), label_r, fill=(240, 214, 150))

canvas.paste(L, (PAD, BAR + PAD))
canvas.paste(R, (PAD + L.width + GAP, BAR + PAD))
canvas.save(out)
print(f'{out} {canvas.size}  (左 {L.size} / 右 {R.size})')
