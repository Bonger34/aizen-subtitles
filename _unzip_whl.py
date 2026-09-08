# -*- coding: utf-8 -*-
"""通用: 下载指定 wheel(名称/版本/平台筛选)并解压到目标目录
用法: python _unzip_whl.py <pypi包名> <版本> <输出目录> [wheel文件名包含串]
"""
import json
import os
import shutil
import sys
import urllib.request
import zipfile

DL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dl'


def main():
    pkg, ver, out, sub = sys.argv[1], sys.argv[2], sys.argv[3], (sys.argv[4] if len(sys.argv) > 4 else '')
    with urllib.request.urlopen(f'https://pypi.org/pypi/{pkg}/{ver}/json', timeout=60) as r:
        d = json.load(r)
    for f in d['urls']:
        fn = f['filename']
        if fn.endswith('.whl') and sub in fn:
            path = os.path.join(DL, fn)
            if not os.path.exists(path):
                print('下载', fn, flush=True)
                with urllib.request.urlopen(f['url'], timeout=300) as r2, open(path, 'wb') as fh:
                    shutil.copyfileobj(r2, fh, 1024 * 512)
            os.makedirs(out, exist_ok=True)
            with zipfile.ZipFile(path) as z:
                z.extractall(out)
            print(f'解压 {fn} -> {out}', flush=True)
            return
    raise SystemExit(f'{pkg} {ver}: 找不到匹配 wheel')


if __name__ == '__main__':
    main()
