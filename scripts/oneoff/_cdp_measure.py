# _cdp_measure.py — 用 Chrome DevTools Protocol 精确测量页面几何(只用标准库)
# 为什么不用无头 Chrome 的 --window-size: 本机实测不可靠 —— 375 与 640 两个宽度渲染出来的
# 截图字节数完全相同, 说明视口根本没变。目测截图更不可靠(会把 5px 的差异看成"截断")。
# 这里直接走 CDP: HTTP 拿 target 的 webSocketDebuggerUrl, 再用标准库手写最小的 WS 客户端。
# 用法: python _cdp_measure.py <url> <宽> <高>
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.request

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 9333
PROF = r'D:\Bonger\Desktop\2026-08-21-18-21-50\.cdp-profile'


class WS:
    """够用就好的 WebSocket 客户端: 只处理文本帧, 不处理分片。"""

    def __init__(self, url, timeout=30):
        _, rest = url.split('://', 1)
        hostport, path = rest.split('/', 1)
        host, port = hostport.split(':')
        self.sock = socket.create_connection((host, int(port)), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f'GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n'
               f'Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n'
               f'Sec-WebSocket-Version: 13\r\n\r\n')
        self.sock.sendall(req.encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.sock.recv(4096)
        if b'101' not in buf.split(b'\r\n')[0]:
            raise RuntimeError(f'握手失败: {buf[:120]!r}')
        self.buf = buf.split(b'\r\n\r\n', 1)[1]

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError('连接被关闭')
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text):
        payload = text.encode()
        header = bytearray([0x81])                       # FIN + text
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126); header += struct.pack('>H', n)
        else:
            header.append(0x80 | 127); header += struct.pack('>Q', n)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def recv(self):
        b0, b1 = self._read(2)
        n = b1 & 0x7F
        if n == 126:
            n = struct.unpack('>H', self._read(2))[0]
        elif n == 127:
            n = struct.unpack('>Q', self._read(8))[0]
        return self._read(n).decode('utf-8', 'replace')


def main():
    url, w, h = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    proc = subprocess.Popen(
        [CHROME, '--headless', '--disable-gpu', '--no-sandbox',
         f'--remote-debugging-port={PORT}', f'--user-data-dir={PROF}',
         '--no-first-run', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ver = None
        for _ in range(60):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version', timeout=1) as r:
                    ver = json.load(r)
                break
            except Exception:
                time.sleep(0.5)
        if not ver:
            raise SystemExit('DevTools 未就绪')
        # 注意: 新版 Chrome 的 /json/new 只接受 PUT(GET 会返回 405)
        req = urllib.request.Request(f'http://127.0.0.1:{PORT}/json/new?about:blank', method='PUT')
        with urllib.request.urlopen(req) as r:
            target = json.load(r)

        ws = WS(target['webSocketDebuggerUrl'])
        counter = [0]

        def cdp(method, params=None):
            counter[0] += 1
            mid = counter[0]
            ws.send(json.dumps({'id': mid, 'method': method, 'params': params or {}}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get('id') == mid:
                    if 'error' in msg:
                        raise RuntimeError(msg['error'])
                    return msg.get('result', {})

        cdp('Emulation.setDeviceMetricsOverride',
            {'width': w, 'height': h, 'deviceScaleFactor': 1, 'mobile': False})
        cdp('Page.enable')
        cdp('Page.navigate', {'url': url})
        time.sleep(3)                                     # 等 DB 异步填统计行

        expr = """
        (function(){
          var q=document.getElementById('query'), cs=getComputedStyle(q);
          var pad=parseFloat(cs.paddingLeft)+parseFloat(cs.paddingRight);
          var t=document.querySelector('.control-top'), f=document.querySelector('.search-form');
          function widthOf(txt){
            var s=document.createElement('span');
            s.style.cssText='position:absolute;visibility:hidden;white-space:nowrap;font:'+cs.font;
            s.textContent=txt; document.body.appendChild(s);
            var w=Math.ceil(s.getBoundingClientRect().width); s.remove(); return w;
          }
          var need=widthOf(q.placeholder);
          var inner=Math.round(q.clientWidth-pad);
          // 候选文案在当前输入框里能不能放下
          var cands={};
          ['检索爱染诚的台词，如：我是爱与善意的传播者、水晶',
           '检索爱染诚的台词，如：水晶',
           '检索爱染诚的台词',
           '检索台词，如：水晶'].forEach(function(t){ cands[t]=widthOf(t); });
          return JSON.stringify({视口:innerWidth+'x'+innerHeight,
            台面宽:Math.round(f.getBoundingClientRect().width),
            控件列宽:Math.round(t.getBoundingClientRect().width),
            输入框内容宽:inner, placeholder需要:need, 被截断:need>inner,
            候选文案宽度:cands, 统计行:document.querySelector('.hero-stats').textContent});
        })()
        """
        res = cdp('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
        data = json.loads(res['result']['value'])
        # 用 ASCII 键名与列宽对齐输出 —— 中文经 PowerShell 管道会被 GBK 解码搞乱
        inner = data['输入框内容宽']
        print(f"viewport={data['视口']:<10} panel={data['台面宽']:<5} "
              f"ctrlcol={data['控件列宽']:<5} input_inner={inner:<5} "
              f"current_need={data['placeholder需要']:<5} truncated={data['被截断']}")
        for text, w in data['候选文案宽度'].items():
            mark = 'OK ' if w <= inner else f'+{w - inner}'
            print(f"    need={w:<5} vs {inner:<5} [{mark:>5}]  {text}")
        print(f"    stats_line={data['统计行']}")
    finally:
        proc.terminate()


if __name__ == '__main__':
    main()
