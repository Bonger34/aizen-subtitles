# _crop.py — 裁出截图的一块区域做原尺寸查看(读图工具会缩大图, 所以先裁小)
# 用法: python _crop.py <输入图> <x> <y> <w> <h> <输出图>
import sys
from PIL import Image

src, x, y, w, h, dst = sys.argv[1], *[int(v) for v in sys.argv[2:6]], sys.argv[6]
im = Image.open(src).convert('RGB')
box = im.crop((x, y, x + w, y + h))
box.save(dst)
print(f'{src} {im.size} -> 裁 ({x},{y},{w},{h}) -> {dst} {box.size}')
