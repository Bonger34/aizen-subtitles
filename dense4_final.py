# -*- coding: utf-8 -*-
"""收敛迭代: 对"疑似漏句 + 短文本"逐条到视频复核, 确认库中没有的补入库。

用法: python dense4_final.py [--apply]
"""
import json
import os
import re
import sys

_NV_DLL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'
_ORT124 = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_ort124'
if os.path.isdir(_NV_DLL):
    os.add_dll_directory(_NV_DLL)
    os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
if os.path.isdir(_ORT124):
    sys.path.insert(0, _ORT124)

import cv2
import numpy as np
from rapidocr import RapidOCR
from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V = os.path.join(B, 'Videos')
CLEAN = os.path.join(B, 'subtitle_clean')
FR = os.path.join(B, 'Web', 'frames')
SRC = os.path.join(B, 'review', 'converge.json')

# 更严格的排除词(片尾演职员表 / 图鉴预告 / 歌词)
CREDIT = ('坂井', '万理子', '渡邊', '渡边', '亮太', '植田梨', '岩崎', '福城', '手島', '手岛',
          '孝祥', '岡本', '冈本', '島田', '及川', '青井', '稲垣', '稻垣', '千春', '商店街相模原',
          '相模原', '多摩市', '城市所以在', '上进行', '什上计', '进进行', '計准行', '计准行',
          '你就陪在我身边', '夕阳', '望而却步', '牵绊', '那句谢谢', '说不出口', '没有永恒',
          '不经意地翻开相册', '仿若能天长地久', '全世界都在等着我', '欢迎来到爱染科技')
GUIDE = ('奥特曼', '奥特战士', '怪兽', '骨兽', '必杀技', '水晶', '身高', '体重', '图鉴', '形态',
         '变身', '巨型生物', '哥莫拉', '格尔吉欧', '传说', '雷德王', '金古桥', '达达', '巴萨',
         '罗索', '布鲁', '泰罗', '赛文', '银河', '迪迦', '欧布', '维克特利', '艾克斯', '赛罗',
         '冲击斩', '多种技能', '空中型', '烈火', '跃水', '进行作战')


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def strip_digits(s):
    return re.sub(r'\d+$', '', re.sub(r'^\d+', '', s))


def score(a, b):
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return min(sum(1 for ch in a if ch in sb) / len(a), sum(1 for ch in b if ch in sa) / len(b))


def ts_of(s):
    return f'{int(s) // 60}m{int(s) % 60:02d}s'


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def main():
    apply = '--apply' in sys.argv
    d = json.load(open(SRC, encoding='utf-8'))
    pool = d['dialogue'] + d['short']
    lib, allt, files = {}, [], set(os.listdir(FR))
    for fn in sorted(os.listdir(CLEAN)):
        if fn.endswith('.json'):
            title = fn[:-5]
            lib[title] = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
            allt += [cn(e.get('text')) for e in lib[title]]
    cands = []
    for c in pool:
        t = strip_digits(cn(c['text']))
        if len(t) < 2:
            continue
        if 'sec' not in c:
            c = {**c, 'sec': sec_of(c['t'])}
        if any(w in t for w in CREDIT) or any(w in t for w in GUIDE):
            continue
        if any(score(t, lt) >= 0.7 for lt in allt if abs(len(lt) - len(t)) <= 6):
            continue
        cands.append({**c, 'text': t})
    print(f'严格过滤后候选 {len(cands)} 条', flush=True)
    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
    })
    caps, ok_list, bad = {}, [], []
    for i, c in enumerate(cands):
        ep, sec, want = c['ep'], c['sec'], cn(c['text'])
        if ep not in caps:
            caps[ep] = cv2.VideoCapture(find_video(ep))
        cap = caps[ep]
        fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
        got, delta = '', 0.0
        for dd in (0.0, -0.4, 0.4):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((sec + dd) * fps)))
            r, fr = cap.read()
            if not r:
                continue
            h, w = fr.shape[:2]
            sy = h / 1080.0
            cc = fr[int(895 * sy):int(1045 * sy), int(100 * (w / 1920.0)):int(1820 * (w / 1920.0))]
            cc = cv2.resize(cc, None, fx=1 / sy, fy=1 / sy, interpolation=cv2.INTER_CUBIC)
            arr = cc.copy()
            mk = np.all(arr > 245, axis=2)
            arr[mk] = [255, 255, 255]
            arr[~mk] = [0, 0, 0]
            rr = ocr(arr)
            t = cn(''.join(rr.txts) if rr.txts else '')
            if sum(1 for ch in want if ch in t) / len(want) >= 0.8:
                got, delta = t, dd
                break
        if not got:
            bad.append(c)
            continue
        ok_list.append({**c, 'ocr': got, 'delta': delta})
        if apply:
            title = [k for k in lib if k.startswith(f'[{ep}]')][0]
            data = lib[title]
            if any(score(cn(e.get('text')), want) >= 0.8 and abs(sec_of(e['timestamp']) - sec) <= 5
                   for e in data):
                continue
            taken = {sec_of(e['timestamp']) for e in data}
            s = sec
            name = f'{ep}_{ts_of(s)}.jpg'
            while s in taken or name in files:
                s += 1
                name = f'{ep}_{ts_of(s)}.jpg'
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((sec + delta) * fps)))
            r, fr = cap.read()
            if r:
                cv2.imwrite(os.path.join(FR, name),
                            cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                            [cv2.IMWRITE_JPEG_QUALITY, 90])
                files.add(name)
            data.append({'timestamp': ts_of(s), 'similarity': 0.0, 'text': c['text']})
            data.sort(key=lambda e: sec_of(e['timestamp']))
            json.dump(data, open(os.path.join(CLEAN, title + '.json'), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
            allt.append(want)
    for cap in caps.values():
        cap.release()
    lines = [f'复核: 通过 {len(ok_list)} / 未通过 {len(bad)}' + ('(已入库)' if apply else '(预演)')]
    for v in ok_list:
        lines.append(f"  {v['ep']} {v['t']:>7s}  [{v['text']}]  画面=[{v['ocr']}]")
    for c in bad:
        lines.append(f"  ?? {c['ep']} {c['t']:>7s}  [{c['text']}] 未通过")
    txt = '\n'.join(lines)
    open(os.path.join(B, 'review', 'dense4_report.txt'), 'w', encoding='utf-8').write(txt)
    print(txt[:5000])


if __name__ == '__main__':
    main()
