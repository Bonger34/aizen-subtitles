# -*- coding: utf-8 -*-
"""爱染科技 logo 资源(矢量 + 位图)

形状出处 —— 剧中真实存在的公司标志, 不是原创:
  · P11 15m36s  爱染诚手里那本《ウルトラマンロッソ》宣传册封面, 黑色印刷版(最清晰)
  · P11 14m49s  他办公室背景墙上的银色立体金属版(同一形状, 不同材质)

形状: 字母 A(三角轮廓, 粗线) 与一个圆环交叠; 圆环偏右略高, A 的右斜线穿环而过。
      A 是**正立**的 —— 册子上因纸张透视看着歪, 墙面金属版更接近正面。

输出:
  docs/assets/aizen_logo.svg   矢量; 描边用 currentColor, 前端可任意改色
  docs/assets/aizen_logo.png   512×512 透明底位图, 描边为白色

用法: python scripts/pipeline/make_aizen_logo.py
"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, 'docs', 'assets')

# 统一归一化到 0-100 坐标系(与 SVG viewBox 一致), 几何参数集中在这里
CX, CY, R = 50.0, 50.0, 40.0
RING = (CX + 0.30 * R, CY - 0.22 * R, 0.58 * R)          # 圆心 x / y / 半径
A_TOP = (CX, CY - 0.95 * R)                               # A 的尖顶
A_L = (CX - 0.74 * R, CY + 0.88 * R)                      # A 左下
A_R = (CX + 0.74 * R, CY + 0.88 * R)                      # A 右下
BAR = 0.64                                                # 横杠位于 A 高度的 64%
W_A = 0.19 * R                                            # A 的笔画宽度
W_RING = W_A * 0.70                                       # 圆环比 A 细

SVG_TMPL = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100" role="img" aria-label="AIZENTECH">
  <g fill="none" stroke="currentColor" stroke-linecap="butt">
    <circle cx="{rcx:.1f}" cy="{rcy:.1f}" r="{rr:.1f}" stroke-width="{rw:.1f}"/>
    <path d="M{tx:.1f} {ty:.1f} L{lx:.1f} {ly:.1f} M{tx:.1f} {ty:.1f} L{rx:.1f} {ry:.1f} M{b1x:.1f} {b1y:.1f} L{b2x:.1f} {b2y:.1f}" stroke-width="{aw:.1f}"/>
  </g>
</svg>
'''


def bar_ends():
    """横杠两端坐标"""
    f = BAR
    return ((A_TOP[0] + (A_L[0] - A_TOP[0]) * f, A_TOP[1] + (A_L[1] - A_TOP[1]) * f),
            (A_TOP[0] + (A_R[0] - A_TOP[0]) * f, A_TOP[1] + (A_R[1] - A_TOP[1]) * f))


def render(size=512, color=(255, 255, 255)):
    """按同一套几何参数画位图版(透明底)"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = size / 100.0
    rcx, rcy, rr = RING
    d.ellipse([(rcx - rr) * k, (rcy - rr) * k, (rcx + rr) * k, (rcy + rr) * k],
              outline=color, width=max(1, round(W_RING * k)))
    aw = max(1, round(W_A * k))
    for a, b in ((A_TOP, A_L), (A_TOP, A_R), bar_ends()):
        d.line([a[0] * k, a[1] * k, b[0] * k, b[1] * k], fill=color, width=aw)
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    rcx, rcy, rr = RING
    (b1x, b1y), (b2x, b2y) = bar_ends()
    svg = SVG_TMPL.format(rcx=rcx, rcy=rcy, rr=rr, rw=W_RING,
                          tx=A_TOP[0], ty=A_TOP[1], lx=A_L[0], ly=A_L[1],
                          rx=A_R[0], ry=A_R[1], b1x=b1x, b1y=b1y, b2x=b2x, b2y=b2y,
                          aw=W_A)
    p_svg = os.path.join(OUT, 'aizen_logo.svg')
    with open(p_svg, 'w', encoding='utf-8') as fh:
        fh.write(svg)
    p_png = os.path.join(OUT, 'aizen_logo.png')
    render(512).save(p_png)
    for p in (p_svg, p_png):
        print('%-32s %6d B' % (os.path.relpath(p, REPO), os.path.getsize(p)))

    # 预览: 三种笔画色 × 深/浅两种底, 顺带核对与实拍的接近程度
    cells = []
    for col in ((255, 255, 255), (0xCB, 0xD0, 0xD8), (0x16, 0x19, 0x20)):
        for bg in ((18, 20, 26), (242, 242, 246)):
            cell = Image.new('RGB', (200, 110), bg)
            ic = render(96, col)
            cell.paste(ic, (52, 7), ic)
            cells.append(cell)
    prev = Image.new('RGB', (3 * 200, 2 * 110), (30, 32, 40))
    for i, c in enumerate(cells):
        prev.paste(c, ((i % 3) * 200, (i // 3) * 110))
    prev.save(os.path.join(REPO, 'review', '_aizen_probe', 'logo_preview.png'))
    print('preview -> review/_aizen_probe/logo_preview.png')


if __name__ == '__main__':
    main()
