# -*- coding: utf-8 -*-
"""make_context_review.py — 12 条前后句核验页

每张卡：同集 ±6s 原始字幕窗口 | 恢复句(A)/画面核定句(B) | 画面帧
按钮：保留A / 采纳B / 两句都留 / 跳过
导出结果 json 供批量落库。
"""
import glob
import json
import os

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
ORIG_DIR = os.path.join(BASE, 'subtitle')
RB = os.path.join(BASE, 'review', 'rollback_risky.json')
LOG = os.path.join(BASE, 'review', 'vision_applied_log.json')
IMG = os.path.join(BASE, 'review', 'ocr_check', 'img')
OUT_DIR = os.path.join(BASE, 'review', 'context_check')

CSS = """
body{font-family:'Microsoft YaHei',sans-serif;background:#f2f4f8;margin:0;padding:0 0 90px}
header{position:sticky;top:0;background:#101e36;color:#fff;padding:12px 20px;
 display:flex;align-items:center;gap:18px;z-index:9}
header h1{font-size:16px;margin:0}
.stats{font-size:12px;color:#9fb0c6}
button{background:#2b76ee;border:none;border-radius:6px;color:#fff;padding:8px 16px;
 cursor:pointer;font-size:13px;margin-left:auto}
.wrap{max-width:980px;margin:18px auto;padding:0 14px}
.card{background:#fff;border:1px solid #d4ddea;border-radius:10px;margin-bottom:14px;
 padding:14px;display:flex;gap:16px}
.left{flex:0 0 300px}
.timeline{font-size:12px;font-family:Consolas,monospace;line-height:1.8;
 background:#f6f8fb;border-radius:8px;padding:10px;border:1px solid #e3e8f0}
.tl-cur{background:#fff3d6;font-weight:700}
.mid{flex:1;min-width:0}
.meta{font-size:12px;color:#8593a8;margin-bottom:8px}
.old{color:#a33;text-decoration:line-through;font-size:14px;margin-bottom:4px}
.new{color:#1a7f37;font-size:15px;font-weight:600}
.imgbox{width:270px}
.imgbox img{display:block;border-radius:6px;margin-bottom:8px;background:#111}
.btns{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap}
.btns button{font-size:12px;padding:5px 14px;border-radius:14px;margin:0}
.btns .ok{background:#e6f4e9;color:#1a7f37;border:1px solid #9ade9a}
.btns .no{background:#eef4ff;color:#2b4eae;border:1px solid #bcd0f5}
.btns .both{background:#fdf0e6;color:#b0603c;border:1px solid #eec9a8}
.btns button.sel{filter:brightness(.92);box-shadow:inset 0 0 0 2px #333}
.notice{background:#fff8e1;border:1px solid #e6cf7a;border-radius:10px;padding:12px 16px;
 margin:14px 0;font-size:13px;color:#7a5c00}
"""

JS = """
const KEY='ctx_review_v1';let st={};
try{st=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
function upd(){
 let a=0,b=0,c=0;
 document.querySelectorAll('.card').forEach(cd=>{
  const id=cd.dataset.id,v=st[id]||'';
  cd.querySelectorAll('button').forEach(bt=>bt.classList.toggle('sel',bt.dataset.v===v));
  if(v==='a')a++;if(v==='b')b++;if(v==='c')c++;
 });
 document.getElementById('sts').textContent=`标记: 保留A ${a} / 采纳B ${b} / 两句都留 ${c} / 待定 ${document.querySelectorAll('.card').length-a-b-c}`;
}
window.addEventListener('DOMContentLoaded',()=>{upd();
 document.querySelectorAll('.btns button').forEach(bt=>bt.onclick=()=>{
  st[bt.closest('.card').dataset.id]=bt.dataset.v;
  localStorage.setItem(KEY,JSON.stringify(st));upd();
 });
 document.getElementById('export').onclick=()=>{
  const out=document.querySelectorAll('.card').length?[]:'';
  document.querySelectorAll('.card').forEach(cd=>{
   const id=cd.dataset.id,v=st[id]||'';
   out.push({id,verdict:v,
    a:cd.querySelector('.old').textContent,
    b:cd.querySelector('.new').textContent});
  });
  const blob=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download='context_check_result.json';a.click();
 };
});
"""


def sec(ts):
    m = ts.split('m')
    return int(m[0]) * 60 + int(m[1].rstrip('s'))


def ts_str(s):
    return f'{s // 60}m{s % 60:02d}s'


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # 原始按集
    orig_rows = {}
    for f in sorted(glob.glob(os.path.join(ORIG_DIR, '*.json'))):
        ep = os.path.basename(f)[1:4]
        orig_rows.setdefault(ep, []).extend(
            json.load(open(f, encoding='utf-8')))

    rb = json.load(open(RB, encoding='utf-8'))
    log = {(x['ep'], x['ts']): x for x in json.load(open(LOG, encoding='utf-8'))}

    cards = []
    for x in rb['rollback']:
        ep, ts = x['ep'], x['ts']
        a_txt = x['restored']
        lg = log.get((ep, ts))
        b_txt = lg['to'] if lg else '(无画面句)'
        s = sec(ts)
        win = sorted([r for r in orig_rows.get(ep, [])
                      if abs(sec(r.get('timestamp', '0m0s')) - s) <= 6],
                     key=lambda r: sec(r['timestamp']))
        tl = ''.join(
            f"<div class='{'tl-cur' if r['timestamp']==ts else ''}'>{r['timestamp']}  {r['text'][:26]}</div>"
            for r in win) or '<div>(无相邻条目)</div>'
        img = os.path.join(IMG, f'{ep}_{ts}.jpg')
        imgc = os.path.join(IMG, f'{ep}_{ts}_c.jpg')
        imgs = ''
        if os.path.exists(img):
            imgs += f'<img src="../ocr_check/img/{ep}_{ts}.jpg" width="270">'
        if os.path.exists(imgc):
            imgs += f'<img src="../ocr_check/img/{ep}_{ts}_c.jpg" width="270" height="52" style="object-fit:contain">'
        if not imgs:
            imgs = '<div style="width:270px;height:120px;background:#eee;display:flex;align-items:center;justify-content:center;color:#999">无图</div>'
        cards.append(f"""
<div class="card" data-id="{ep}_{ts}">
  <div class="left">
    <div class="meta">同集 ±6s 原始字幕（高亮=本条 ts）</div>
    <div class="timeline">{tl}</div>
  </div>
  <div class="mid">
    <div class="meta">{ep} · {ts}</div>
    <div class="old">A 恢复句(现状库)：{a_txt[:36]}</div>
    <div class="new">B 画面核定句：{b_txt[:36]}</div>
    <div class="btns">
      <button class="ok" data-v="a">A 保留原句</button>
      <button class="no" data-v="b">B 采纳画面句</button>
      <button class="both" data-v="c">C 两句都留</button>
    </div>
  </div>
  <div class="imgbox">{imgs}</div>
</div>""")

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>前后句上下文核验</title><style>{CSS}</style></head><body>
<header><h1>前后句上下文核验（{len(cards)} 条）</h1>
<span class="stats" id="sts">加载中…</span>
<button id="export">导出结果</button></header>
<div class="wrap">
<div class="notice"><b>怎么看：</b>左侧是该条 ±6s 的<b>原始字幕</b>（判断 A/B 是否相邻对白）。
右图验证画面。判定：<u>A</u>=B只是画面句，本条确实是A；<u>B</u>=画面句对，A不存在(可删除)；
<u>C</u>=两句都是真实台词（前后句），B要另立一条。完成后导出 json 发我。</div>
{''.join(cards)}
</div><script>{JS}</script></body></html>"""
    with open(os.path.join(OUT_DIR, 'index.html'), 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f'输出: {OUT_DIR}/index.html ({len(cards)} 张卡)')


if __name__ == '__main__':
    main()
