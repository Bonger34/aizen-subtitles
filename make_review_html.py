# -*- coding: utf-8 -*-
"""make_review_html.py — 生成 OCR 复核可视化核对页

输入:
  review/ocr_final_risky.json      159 条内容变化候选（from→to）
  review/ocr_revision_candidates.json  140 条待核（lib→ocr）
输出:
  review/ocr_check/index.html       核对页（内嵌数据+JS，支持标记/导出）
  review/ocr_check/img/xxx.jpg      每条对应画面帧 + 字幕带放大图
用法: python make_review_html.py
"""
import glob
import json
import os
import re

import cv2

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO_DIR = os.path.join(BASE, 'Videos')
OUT_DIR = os.path.join(BASE, 'review', 'ocr_check')
IMG_DIR = os.path.join(OUT_DIR, 'img')
SUBTITLE_AREA = (100, 895, 1820, 985)

CSS = """
body{font-family:'Microsoft YaHei',sans-serif;background:#f2f4f8;margin:0;padding:0 0 90px}
header{position:sticky;top:0;background:#101e36;color:#fff;padding:12px 20px;
 display:flex;align-items:center;gap:18px;z-index:9}
header h1{font-size:16px;margin:0}
.stats{font-size:12px;color:#9fb0c6}
button{background:#2b76ee;border:none;border-radius:6px;color:#fff;padding:8px 16px;
 cursor:pointer;font-size:13px;margin-left:auto}
button:hover{background:#1756bd}
.wrap{max-width:900px;margin:18px auto;padding:0 14px}
.card{background:#fff;border:1px solid #d4ddea;border-radius:10px;margin-bottom:12px;
 overflow:hidden;display:flex;gap:14px;padding:12px}
.card img{display:block;border-radius:6px;background:#e2eaf4}
.imgs{flex:0 0 auto;display:flex;flex-direction:column;gap:8px}
.info{flex:1;min-width:0}
.meta{font-family:Consolas,monospace;font-size:12px;color:#8593a8;margin-bottom:6px}
.tag{display:inline-block;font-size:11px;padding:1px 8px;border-radius:10px;margin-left:6px}
.tag.risky{background:#fff3e6;color:#b0603c;border:1px solid #eec9a8}
.tag.cand{background:#eef4ff;color:#2b4eae;border:1px solid #bcd0f5}
.old{color:#a33;text-decoration:line-through;font-size:14px}
.new{color:#1a7f37;font-size:15px;font-weight:600;margin-top:2px}
.ocr{color:#5a6a85;font-size:13px;margin-top:4px;font-style:italic}
.btns{margin-top:10px;display:flex;gap:8px}
.btns button{margin:0;font-size:12px;padding:5px 14px;border-radius:14px}
.btns .ok{background:#e6f4e9;color:#1a7f37;border:1px solid #9ade9a}
.btns .ok.sel{background:#1a7f37;color:#fff}
.btns .no{background:#fdeaea;color:#a33;border:1px solid #f3a3a3}
.btns .no.sel{background:#a33;color:#fff}
.card.done{border-color:#8f8;box-shadow:0 0 0 2px #cfe8cf}
.card.bad{border-color:#f88;box-shadow:0 0 0 2px #f6c9c9}
.notice{background:#fff8e1;border:1px solid #e6cf7a;border-radius:10px;padding:12px 16px;
 margin:14px 0;font-size:13px;color:#7a5c00}
.notice b{color:#a33}
"""

JS = """
const STORE_KEY='ocr_check_v1';
let state={};
try{state=JSON.parse(localStorage.getItem(STORE_KEY)||'{}')}catch(e){}
function render(){
 let ok=0,bad=0;
 document.querySelectorAll('.card').forEach(c=>{
  const id=c.dataset.id, st=state[id]||'';
  c.classList.toggle('done',st==='ok');
  c.classList.toggle('bad',st==='no');
  c.querySelector('.ok').classList.toggle('sel',st==='ok');
  c.querySelector('.no').classList.toggle('sel',st==='no');
  if(st==='ok')ok++;if(st==='no')bad++;
 });
 document.getElementById('sts').textContent=`已标记 正确 ${ok} / 错误 ${bad} / 待定 ${document.querySelectorAll('.card').length-ok-bad}`;
}
function set(id,v){state[id]=v;localStorage.setItem(STORE_KEY,JSON.stringify(state));render();}
function exportJSON(){
 const out=[];
 document.querySelectorAll('.card').forEach(c=>{
  const id=c.dataset.id, st=state[id]||'';
  const meta=c.querySelector('.meta').textContent;
  out.push({id, verdict:st, ...(st?{meta}:{})});
 });
 const blob=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});
 const a=document.createElement('a');a.href=URL.createObjectURL(blob);
 a.download='ocr_check_result.json';a.click();
}
window.addEventListener('DOMContentLoaded',()=>{render();
 document.querySelectorAll('.ok').forEach(b=>b.onclick=()=>set(b.closest('.card').dataset.id,'ok'));
 document.querySelectorAll('.no').forEach(b=>b.onclick=()=>set(b.closest('.card').dataset.id,'no'));
 document.getElementById('export').onclick=exportJSON;});
"""


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    # 合并去重
    risky = json.load(open(os.path.join(BASE, 'review', 'ocr_final_risky.json'),
                          encoding='utf-8'))
    cands = json.load(open(os.path.join(BASE, 'review', 'ocr_revision_candidates.json'),
                            encoding='utf-8'))
    items = []
    seen = set()
    for x in risky:
        k = (x['ep'], x['ts'])
        if k not in seen:
            seen.add(k)
            items.append({'ep': x['ep'], 'ts': x['ts'], 'old': x['from'],
                          'new': x['to'], 'kind': 'risky'})
    for x in cands:
        k = (x['ep'], x['ts'])
        if k not in seen:
            seen.add(k)
            items.append({'ep': x['ep'], 'ts': x['ts'], 'old': x['lib'],
                          'new': x['ocr'], 'kind': 'cand'})
    print(f'待核 {len(items)} 条', flush=True)

    cards = []
    for it in items:
        ep, ts = it['ep'], it['ts']
        video = [os.path.join(VIDEO_DIR, v) for v in os.listdir(VIDEO_DIR)
                 if v.startswith(f'[{ep}]') and v.lower().endswith('.mp4')]
        if not video:
            continue
        sec = int(ts.rstrip('s').split('m')[0]) * 60 + int(ts.split('m')[1].rstrip('s'))
        cap = cv2.VideoCapture(video[0])
        cap.set(cv2.CAP_PROP_POS_MSEC, int(sec * 1000 + 800))
        ret, frame = cap.read()
        cap.release()
        fid = f'{ep}_{ts}'
        if frame is not None:
            cv2.imwrite(os.path.join(IMG_DIR, f'{fid}.jpg'), frame,
                        [cv2.IMWRITE_JPEG_QUALITY, 82])
            crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3],
                         SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
            cv2.imwrite(os.path.join(IMG_DIR, f'{fid}_c.jpg'), crop,
                        [cv2.IMWRITE_JPEG_QUALITY, 88])
            imgs = (f'<img src="img/{fid}.jpg" width="270">'
                    f'<img src="img/{fid}_c.jpg" width="270" height="52" '
                    'style="object-fit:contain;background:#111">')
        else:
            imgs = '<div style="width:270px;height:150px;background:#ddd;display:flex;' \
                   'align-items:center;justify-content:center;color:#888">读取失败</div>'
        tag = ('<span class="tag risky">替换类</span>' if it['kind'] == 'risky'
               else '<span class="tag cand">待核</span>')
        cards.append(f"""
<div class="card" data-id="{fid}">
  <div class="imgs">{imgs}</div>
  <div class="info">
    <div class="meta">{ep} · {ts}{tag}</div>
    <div class="old">{it['old']}</div>
    <div class="new">{it['new']}</div>
    <div class="btns">
      <button class="ok">✔ 正确</button>
      <button class="no">✘ 应为原文本</button>
    </div>
  </div>
</div>""")

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>OCR 复核核对页</title><style>{CSS}</style></head><body>
<header><h1>OCR 复核核对页</h1>
<span class="stats" id="sts">加载中…</span>
<button id="export">导出标记结果</button></header>
<div class="wrap">
<div class="notice"><b>用法：</b>看图（上=画面，下=字幕带放大），对照左右文本。
<u>正确</u>=采纳右测文本；<u>错误</u>=保留原文本；不点=跳过。标记记录在本机，刷新不丢，
完成后点「导出标记结果」下载 json 发我，我来批量入库。</div>
{''.join(cards)}
</div>
<script>{JS}</script></body></html>"""
    with open(os.path.join(OUT_DIR, 'index.html'), 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f'输出: {OUT_DIR}/index.html（{len(cards)} 张卡片）')


if __name__ == '__main__':
    main()
