# -*- coding: utf-8 -*-
"""第四轮: 只复核"可能是台词"的候选(先前排除片头片尾歌词/版权卡/职员表/纯数字), 逐条到视频验证后入库。

关键修正: 不再用"奥特曼/水晶/形态"等关键词排除候选 —— 上一轮那样会误杀真台词
(如「奥特战士真的超棒的」「有人要订购10000件」)。改为**按跨集重复**识别歌词与固定字幕。
"""
import json
import os
import re
import sys
import collections

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
D2 = os.path.join(B, 'review', 'dense2')
COPY = re.compile(r'版权|新创华|文化发展|中国大陆|上海新|株式会社')
# 只在片头/片尾/版权卡这些固定段位上排除(不按内容词排除)
LYRIC_WIN = [(40, 220), (1340, 1560)]


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def strip_digits(s):
    return re.sub(r'\d+$', '', re.sub(r'^\d+', '', s))


def score(a, b):
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return min(sum(1 for ch in a if ch in sb) / len(a), sum(1 for ch in b if ch in sa) / len(b))


def sec_of(t):
    return int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))


def ts_of(s):
    return f'{s // 60}m{s % 60:02d}s'


def find_video(ep):
    for f in os.listdir(V):
        if f.startswith(f'[{ep}]') and f.lower().endswith('.mp4'):
            return os.path.join(V, f)


def main():
    apply = '--apply' in sys.argv
    lib, allt = {}, []
    for fn in sorted(os.listdir(CLEAN)):
        if fn.endswith('.json'):
            lib[fn[:-5]] = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
            allt += [cn(e.get('text')) for e in lib[fn[:-5]]]
    files = set(os.listdir(FR))
    # 收集候选
    pool = []
    for f in sorted(os.listdir(D2)):
        if not f.endswith('.json'):
            continue
        d = json.load(open(os.path.join(D2, f), encoding='utf-8'))
        ep = d['ep']
        for c in d['cands']:
            t = strip_digits(cn(c['text']))
            if len(t) < 2:
                continue
            if len(re.sub(r'[^0-9]', '', t)) / max(1, len(t)) > 0.34:
                continue
            if COPY.search(t):
                continue
            if any(a <= c['sec'] <= b for a, b in LYRIC_WIN):
                continue
            if any(score(t, lt) >= 0.8 for lt in allt if abs(len(lt) - len(t)) <= 4):
                continue
            pool.append({'ep': ep, 'sec': c['sec'], 't': c['t'], 'text': c['text'], 'key': t})
    rep = collections.Counter(p['key'] for p in pool)
    pool = [p for p in pool if rep[p['key']] < 3]
    print(f'候选池(排除歌词段/版权卡/跨集重复后) {len(pool)} 条', flush=True)
    ocr = RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': True,
        'Det.model_type': ModelType.MEDIUM, 'Det.ocr_version': OCRVersion.PPOCRV6,
        'Det.lang': LangDet.MULTI,
        'Rec.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': [3, 48, 1536], 'Rec.rec_batch_num': 1,
    })
    caps, hits = {}, []
    for i, c in enumerate(pool):
        if i % 100 == 0:
            print(f'  {i}/{len(pool)}', flush=True)
        ep, sec, want = c['ep'], c['sec'], c['key']
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
            g = cn(''.join(rr.txts) if rr.txts else '')
            if sum(1 for ch in want if ch in g) / len(want) >= 0.8:
                got, delta = g, dd
                break
        if not got:
            continue
        if any(score(cn(got), lt) >= 0.8 for lt in allt if abs(len(lt) - len(cn(got))) <= 6):
            continue
        # --- 入库前的最后过滤 ---
        if v_ep := c['ep']:
            if v_ep == 'P25' and sec >= 21 * 60:
                continue                              # P25 片尾职员表段
        if rep[c['key']] >= 2:
            continue                                  # 跨集重复(歌词碎片)
        if any(c['key'] in lt and len(c['key']) < len(lt) for lt in allt):
            continue                                  # 只是已有条目的片段
        hits.append({**c, 'ocr': got, 'delta': delta})
    print(f'复核通过 {len(hits)} 条' + ('(落盘中)' if apply else '(预演)'))
    for v in hits:
        print(f"   {v['ep']} {v['t']:>7s}  [{v['key']}]")
    if apply:
        for v in hits:
            ep = v['ep']
            title = [k for k in lib if k.startswith(f'[{ep}]')][0]
            data = lib[title]
            taken = {sec_of(e['timestamp']) for e in data}
            s = v['sec']
            name = f'{ep}_{ts_of(s)}.jpg'
            while s in taken or name in files:
                s += 1
                name = f'{ep}_{ts_of(s)}.jpg'
            cap = caps[ep]
            fps = cap.get(cv2.CAP_PROP_FPS) or 23.98
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(round((s + v['delta']) * fps)))
            r, fr = cap.read()
            if r:
                cv2.imwrite(os.path.join(FR, name),
                            cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA),
                            [cv2.IMWRITE_JPEG_QUALITY, 90])
                files.add(name)
            data.append({'timestamp': ts_of(s), 'similarity': 0.0, 'text': v['key']})
            data.sort(key=lambda e: sec_of(e['timestamp']))
            json.dump(data, open(os.path.join(CLEAN, title + '.json'), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
            allt.append(cn(v['key']))
    for cap in caps.values():
        cap.release()


if __name__ == '__main__':
    main()
