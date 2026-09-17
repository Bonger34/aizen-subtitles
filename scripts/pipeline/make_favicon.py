# -*- coding: utf-8 -*-
"""生成站点图标: 场景色块版

语法照上游 favicon —— 把一张实拍画面压成几个基本色块, 一眼能读出场景。
内容换成《罗布奥特曼》爱染诚:

    红蓝背景   = 罗布(Rosso) + 布鲁(Blu), R/B 本来就是红蓝
    肉色方块   = 爱染诚的脸
    白色梯形   = 他的白西装(上游原图标是黑西装, 这里正好反色)
    粉色窄条   = 粉领带(站点色板 --blush 注释即"粉领带(爱染诚标记)")
    黑框白条   = 字幕 —— 剧中是白字镶黑边, 压成"黑框 + 白条"
    左上角     = 爱染科技 logo(剧中真实标志, 几何与出处见 make_aizen_logo.py)

注意: 白条必须用纯白 #FFFFFF。站点白西装是 #F7F2EA, 同色会让白条在白西装上隐形。

输出: docs/favicon.ico(16/32/48/64) · docs/apple-touch-icon.png · docs/icon.svg
用法: python scripts/pipeline/make_favicon.py
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, 'docs')
sys.path.insert(0, HERE)
from make_aizen_logo import RING, A_TOP, A_L, A_R, BAR, W_A, W_RING  # noqa: E402

S = 1024
RED = (0xA8, 0x2E, 0x34)          # 罗布红
BLUE = (0x23, 0x4A, 0x8A)         # 布鲁蓝
SKIN = (0xE6, 0xBE, 0x9C)         # 肤色
SUIT = (0xF7, 0xF2, 0xEA)         # 白西装(站点 --white)
TIE = (0xF2, 0xA7, 0xBC)          # 粉领带(站点 --blush)
COLLAR = (0x3A, 0x3E, 0x4A)       # 领口深色 V
DARK = (0x14, 0x17, 0x1F)         # 字幕黑边
WHITE = (0xFF, 0xFF, 0xFF)        # 字幕白字
SILVER = (0xCB, 0xD0, 0xD8)       # 爱染科技 logo 的银色

ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64)]
# logo 在图标里的位置与大小(归一化), 与场景其余部分同一坐标系
LOGO_CX, LOGO_CY, LOGO_R = 0.158, 0.140, 0.088

# 场景几何: (x0, y0, x1, y1) 归一化
BG_DIAG = [(0.58, 0), (1, 0), (1, 1), (0.22, 1)]
SUIT_POLY = [(0.320, 0.535), (0.680, 0.535), (0.940, 1.0), (0.060, 1.0)]
COLLAR_POLY = [(0.437, 0.535), (0.563, 0.535), (0.50, 0.745)]
TIE_POLY = [(0.478, 0.548), (0.522, 0.548), (0.534, 0.855), (0.466, 0.855)]
FACE = (0.392, 0.262, 0.608, 0.535)
SUB_EDGE = (0.150, 0.818, 0.780, 0.922)
SUB_TEXT = (0.186, 0.838, 0.744, 0.902)


def draw_logo(d, size):
    """爱染科技 logo: A 与圆环交叠

    与 make_aizen_logo.py 共用同一套几何 —— 那里的坐标是 0-100 空间、R=40,
    这里把它整体缩放并搬到左上方 (LOGO_CX, LOGO_CY), 半径取 LOGO_R。
    """
    scale = (LOGO_R * size) / 40.0
    cx, cy = LOGO_CX * size, LOGO_CY * size
    rcx, rcy, rr = RING
    ox, oy, orr = cx + (rcx - 50) * scale, cy + (rcy - 50) * scale, rr * scale
    d.ellipse([ox - orr, oy - orr, ox + orr, oy + orr],
              outline=SILVER, width=max(2, round(W_RING * scale)))
    pt = lambda q: (cx + (q[0] - 50) * scale, cy + (q[1] - 50) * scale)
    aw = max(2, round(W_A * scale))
    top, lf, rt = pt(A_TOP), pt(A_L), pt(A_R)
    d.line([top, lf], fill=SILVER, width=aw)
    d.line([top, rt], fill=SILVER, width=aw)
    b1 = (top[0] + (lf[0] - top[0]) * BAR, top[1] + (lf[1] - top[1]) * BAR)
    b2 = (top[0] + (rt[0] - top[0]) * BAR, top[1] + (rt[1] - top[1]) * BAR)
    d.line([b1, b2], fill=SILVER, width=aw)


def build(size=S):
    img = Image.new('RGB', (size, size), BLUE)
    d = ImageDraw.Draw(img)
    P = lambda seq: [(round(a * size), round(b * size)) for a, b in seq]
    B = lambda b: [round(v * size) for v in b]
    d.polygon(P(BG_DIAG), fill=RED)
    d.polygon(P(SUIT_POLY), fill=SUIT)
    d.polygon(P(COLLAR_POLY), fill=COLLAR)
    d.polygon(P(TIE_POLY), fill=TIE)
    d.rectangle(B(FACE), fill=SKIN)
    d.rectangle(B(SUB_EDGE), fill=DARK)
    d.rectangle(B(SUB_TEXT), fill=WHITE)
    draw_logo(d, size)
    return img


def svg():
    """矢量版 —— 现代浏览器按任意尺寸渲染都清晰"""
    def pts(seq):
        return ' '.join('%.1f,%.1f' % (a * 100, b * 100) for a, b in seq)

    k = LOGO_R * 100 / 40.0
    cx, cy = LOGO_CX * 100, LOGO_CY * 100
    rcx, rcy, rr = RING
    ox, oy, orr = cx + (rcx - 50) * k, cy + (rcy - 50) * k, rr * k
    p = lambda q: (cx + (q[0] - 50) * k, cy + (q[1] - 50) * k)
    top, lf, rt = p(A_TOP), p(A_L), p(A_R)
    b1 = (top[0] + (lf[0] - top[0]) * BAR, top[1] + (lf[1] - top[1]) * BAR)
    b2 = (top[0] + (rt[0] - top[0]) * BAR, top[1] + (rt[1] - top[1]) * BAR)
    hexc = lambda c: '#%02X%02X%02X' % c
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100" role="img" aria-label="爱染诚 台词档案馆">'
        '<rect width="100" height="100" fill="%s"/>'
        '<polygon points="%s" fill="%s"/>'
        '<polygon points="%s" fill="%s"/>'
        '<polygon points="%s" fill="%s"/>'
        '<polygon points="%s" fill="%s"/>'
        '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
        '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
        '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
        '<g fill="none" stroke="%s" stroke-linecap="butt">'
        '<circle cx="%.1f" cy="%.1f" r="%.1f" stroke-width="%.1f"/>'
        '<path d="M%.1f %.1f L%.1f %.1f M%.1f %.1f L%.1f %.1f M%.1f %.1f L%.1f %.1f" stroke-width="%.1f"/>'
        '</g></svg>'
    ) % (
        hexc(BLUE), pts(BG_DIAG), hexc(RED), pts(SUIT_POLY), hexc(SUIT),
        pts(COLLAR_POLY), hexc(COLLAR), pts(TIE_POLY), hexc(TIE),
        FACE[0] * 100, FACE[1] * 100, (FACE[2] - FACE[0]) * 100, (FACE[3] - FACE[1]) * 100, hexc(SKIN),
        SUB_EDGE[0] * 100, SUB_EDGE[1] * 100, (SUB_EDGE[2] - SUB_EDGE[0]) * 100, (SUB_EDGE[3] - SUB_EDGE[1]) * 100, hexc(DARK),
        SUB_TEXT[0] * 100, SUB_TEXT[1] * 100, (SUB_TEXT[2] - SUB_TEXT[0]) * 100, (SUB_TEXT[3] - SUB_TEXT[1]) * 100, hexc(WHITE),
        hexc(SILVER),
        ox, oy, orr, W_RING * k,
        top[0], top[1], lf[0], lf[1], top[0], top[1], rt[0], rt[1], b1[0], b1[1], b2[0], b2[1], W_A * k,
    )


def main():
    os.makedirs(OUT, exist_ok=True)
    icon = build(S)
    p_ico = os.path.join(OUT, 'favicon.ico')
    icon.save(p_ico, format='ICO', sizes=ICO_SIZES)
    p_touch = os.path.join(OUT, 'apple-touch-icon.png')
    icon.resize((180, 180), Image.Resampling.LANCZOS).save(p_touch)
    p_svg = os.path.join(OUT, 'icon.svg')
    with open(p_svg, 'w', encoding='utf-8') as fh:
        fh.write(svg())
    icon.resize((512, 512), Image.Resampling.LANCZOS).save(
        os.path.join(REPO, 'review', '_aizen_probe', 'icon_512.png'))
    for p in (p_ico, p_touch, p_svg):
        print('%-30s %7d B' % (os.path.relpath(p, REPO), os.path.getsize(p)))


if __name__ == '__main__':
    main()
