# -*- coding: utf-8 -*-
"""下载 pefile 纯 py wheel 解压到 workspace, 供导入表解析"""
import os
import shutil
import urllib.request
import zipfile

OUT = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_pylibs'
os.makedirs(OUT, exist_ok=True)
url = 'https://files.pythonhosted.org/packages/5d/41/12b8eaf1e4f32d133cf2e9c4e7f89a5a4f5bd0ec07c6f8d1e6f432b9d4d9/pefile-2024.8.26-py3-none-any.whl'
# 用 PyPI JSON 获取真实 URL, 避免硬编码哈希
import json
with urllib.request.urlopen('https://pypi.org/pypi/pefile/json') as r:
    d = json.load(r)
files = [f for f in d['urls'] if f['filename'].endswith('.whl')]
if not files:
    raise SystemExit('no wheel')
f = files[0]
print('下载', f['filename'])
with urllib.request.urlopen(f['url']) as r, open(os.path.join(OUT, f['filename']), 'wb') as fh:
    shutil.copyfileobj(r, fh, 1024 * 256)
with zipfile.ZipFile(os.path.join(OUT, f['filename'])) as z:
    z.extractall(OUT)
print('解压完成 ->', OUT)
