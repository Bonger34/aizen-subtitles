# -*- coding: utf-8 -*-
"""q_subband.py — 1080p 原帧字幕行定位 + 干净裁切(解决"白衬衫吃掉字幕行"的问题)。

问题: 白像素行剖面法在有大面积白衣物的画面上失效。实测 P01 t=537.81s(字幕「甚至还有点」)
白掩膜剖面 y840~1075 全程 130~275/1920 近乎平坦, 行阈值取 0.12~0.9 都切不出单行, OCR 返回空。

判据(实测有效): 中文字幕是"纯白字 + 黑描边", 白衬衫则是一整块白、没有黑边。于是
  白边掩膜 = 白像素 ∩ 邻域存在暗像素
在 P01 537.81s 上该掩膜的剖面在 y905~975 之外**恒为 0**, 峰值 245@y964, 干净地把字幕行
从衬衫里剥出来。再用连通域剔除"白色大块"(衣物/背景), 只留单字量级的小块 → 实心字形。

坐标约定: 所有函数的 y/x 都是**传入图像自身的像素坐标**(本管线的图像都是 1920x1080 原生
分辨率, 故与 1080p 坐标一致); 传入带宽切片时调用方自行减去 y 偏移。

自测: python q_subband.py P01 537.81 P02 120
"""
import os
import sys

import cv2
import numpy as np

from q_common import SCAN_TOP, SCAN_BOT, X0, X1

W_THR = 200          # 白像素阈值
D_THR = 90           # 暗像素阈值(描边/阴影)
NEAR = 9             # 邻域膨胀核尺寸
BAND_RATIO = 0.35    # 行带阈值 = 白边掩膜剖面容量的该比例
ROW_GAP = 8          # 行段合并间隙
MIN_BAND_H = 14      # 行带高度下限
PAD_Y = 6            # 行带上下扩边(收进描边)
MAX_CC_W = 220       # 连通域宽上限: 超过视为衣物/背景大块
MAX_CC_H = 110
MIN_CC_A = 120


def edge_white(img, w_thr=W_THR, d_thr=D_THR, near=NEAR):
    """白边掩膜: 白像素 ∩ 邻域存在暗像素。字幕描边外的白像素在这里被保留, 纯白衣物被排除。"""
    mn, mx = img.min(axis=2), img.max(axis=2)
    white = mn > w_thr
    dark = mx < d_thr
    near_d = cv2.dilate(dark.astype(np.uint8), np.ones((near, near), np.uint8)) > 0
    return white, white & near_d


def band_rows(img, top=SCAN_TOP, bot=SCAN_BOT, ratio=BAND_RATIO, w_thr=W_THR, d_thr=D_THR):
    """定位字幕行带, 返回 img 坐标的 [(y0, y1)] —— 0/1/2 段(两行字幕时为 2 段)。

    掩膜只在扫描区上下各留 NEAR*2 行内计算 —— 对整幅 1080p 做 dilate 会白花约 4 倍时间。
    """
    h = img.shape[0]
    t, b = max(0, int(top)), min(h, int(bot))
    if b - t < MIN_BAND_H:
        return []
    o = max(0, t - NEAR * 2)
    e = min(h, b + NEAR * 2)
    _, edge = edge_white(img[o:e], w_thr, d_thr)
    x0, x1 = int(X0 * img.shape[1] / 1920.0), int(X1 * img.shape[1] / 1920.0)
    prof = edge[t - o:b - o, x0:x1].sum(axis=1)
    if prof.max() < 5:
        return []
    thr = max(4, int(prof.max() * ratio))
    ys = np.where(prof >= thr)[0]
    runs = []
    for y in ys:
        if runs and y - runs[-1][1] <= ROW_GAP:
            runs[-1][1] = int(y)
        else:
            runs.append([int(y), int(y)])
    out = []
    for a, bb in runs:
        if bb - a + 1 < MIN_BAND_H:
            continue
        out.append((max(0, t + a - PAD_Y), min(h, t + bb + PAD_Y + 1)))
    return out


def glyph_crop(img, y0, y1, pad=12, w_thr=W_THR, max_cc_w=MAX_CC_W, max_cc_h=MAX_CC_H,
               min_cc_a=MIN_CC_A):
    """在 [y0,y1) 内剔除大块白(衣物/背景), 返回 (x0, x1, 实心字形二值图) 或 None。

    w_thr / max_cc_w / max_cc_h / min_cc_a 可在"放宽档"下调 —— 实测残留条目的主因是
    **识别读漏**(如库[真不愧是爱染先生] 只读到[真不愧先生]), 用更松的白阈值与连通域
    上下限能把偏暗/偏小的字捞回来。
    """
    h, w = img.shape[:2]
    a, b = max(0, int(y0)), min(h, int(y1))
    sub = img[a:b]
    if sub.size == 0:
        return None
    white = (sub.min(axis=2) > w_thr)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(white.astype(np.uint8), 8)
    if n <= 1:
        return None
    w_, h_, a_ = stats[1:, cv2.CC_STAT_WIDTH], stats[1:, cv2.CC_STAT_HEIGHT], stats[1:, cv2.CC_STAT_AREA]
    good = np.where((w_ <= max_cc_w) & (h_ <= max_cc_h) & (a_ >= min_cc_a))[0] + 1
    if good.size == 0:
        return None
    # 用一次 isin 取掩膜: 逐个连通域做 keep[lab==i] 是 O(连通域数 × 全图), 演职员表那种
    # 上千个小字的画面上会把单帧耗时推到几十秒。
    keep = np.isin(lab, good)
    nz = np.where(keep.sum(axis=0) > 0)[0]
    x0 = max(0, int(nz[0]) - pad)
    x1 = min(w, int(nz[-1]) + pad)
    out = np.zeros((sub.shape[0], x1 - x0), np.uint8)
    out[keep[:, x0:x1]] = 255
    return x0, x1, cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)


def read_subs(ocr, img, top=SCAN_TOP, bot=SCAN_BOT, ratio=BAND_RATIO, paths=('bin', 'raw'),
              w_thr=W_THR, d_thr=D_THR, max_cc_w=MAX_CC_W, max_cc_h=MAX_CC_H, min_cc_a=MIN_CC_A):
    """在 img 的 y∈[top,bot) 区域定位字幕行并识别。

    返回 [(y0, y1, x0, x1, txt_bin, txt_raw)], y/x 均为 img 坐标。空列表 = 该帧无字幕。
    放宽档用法: read_subs(..., w_thr=180, max_cc_w=400, min_cc_a=60) —— 用于救回偏暗/偏小的字。
    """
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    out = []
    for y0, y1 in band_rows(img, top, bot, ratio, w_thr, d_thr):
        g = glyph_crop(img, y0, y1, w_thr=w_thr, max_cc_w=max_cc_w, max_cc_h=max_cc_h,
                       min_cc_a=min_cc_a)
        if g is None:
            continue
        x0, x1, binimg = g
        tb = tr = ''
        if 'bin' in paths:
            r = ocr.text_rec(TextRecInput(img=binimg))
            tb = r.txts[0] if r.txts else ''
        if 'raw' in paths:
            raw = img[max(0, y0 - PAD_Y):y1 + PAD_Y, x0:x1]
            if raw.size:
                r = ocr.text_rec(TextRecInput(img=raw))
                tr = r.txts[0] if r.txts else ''
        out.append((y0, y1, x0, x1, tb, tr))
    return out


# ---------------------------------------------------------------- 自测
def _read_frame(ep, t, video_dir):
    vid = [os.path.join(video_dir, v) for v in os.listdir(video_dir)
           if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')][0]
    cap = cv2.VideoCapture(vid)
    fps = cap.get(cv2.CAP_PROP_FPS)
    n, fno = 0, int(round(t * fps))
    while n < fno:
        cap.grab()
        n += 1
    ok, fr = cap.read()
    cap.release()
    return fr


def main():
    from q_common import build_engine
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ocr = build_engine()
    ocr.text_rec(TextRecInput(img=np.zeros((64, 512, 3), np.uint8)))
    for i in range(1, len(sys.argv), 2):
        ep, t = sys.argv[i], float(sys.argv[i + 1])
        fr = _read_frame(ep, t, os.path.join(B, 'Videos'))
        rows = read_subs(ocr, fr)
        print(f'\n{ep} t={t}s 字幕行 {len(rows)} 条')
        for y0, y1, x0, x1, tb, tr in rows:
            print(f'   y{y0}-{y1} x{x0}-{x1} bin=[{tb}] raw=[{tr}]')


if __name__ == '__main__':
    main()
