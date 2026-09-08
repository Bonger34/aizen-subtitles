# -*- coding: utf-8 -*-
"""下载指定 onnxruntime-gpu wheel, 检查 providers_cuda.dll 的 cublas 依赖版本"""
import io
import json
import os
import shutil
import sys
import urllib.request
import zipfile

sys.path.insert(0, r'D:\Bonger\Desktop\2026-08-21-18-21-50\_pylibs')
import pefile

DL = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dl'
VER = sys.argv[1] if len(sys.argv) > 1 else '1.28.0'


def get_wheel_url(ver):
    with urllib.request.urlopen(f'https://pypi.org/pypi/onnxruntime-gpu/{ver}/json', timeout=60) as r:
        d = json.load(r)
    for f in d['urls']:
        if f['filename'].endswith('cp313-cp313-win_amd64.whl'):
            return f['filename'], f['url']
    raise SystemExit('no wheel')


fn, url = get_wheel_url(VER)
path = os.path.join(DL, fn)
if not os.path.exists(path):
    print('下载', fn, flush=True)
    with urllib.request.urlopen(url, timeout=300) as r, open(path, 'wb') as fh:
        shutil.copyfileobj(r, fh, 1024 * 512)
    print('  完成', flush=True)

with zipfile.ZipFile(path) as z:
    name = [n for n in z.namelist() if n.endswith('onnxruntime_providers_cuda.dll')]
    if not name:
        print('wheel 中没有 providers_cuda.dll'); raise SystemExit(1)
    data = z.read(name[0])
    pe = pefile.PE(data=data, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    deps = [e.dll.decode() for e in pe.DIRECTORY_ENTRY_IMPORT]
    print(f'{VER} providers_cuda 依赖: {[x for x in deps if "cuda" in x.lower() or "cudnn" in x.lower() or "cublas" in x.lower()]}')
print('wheel 路径:', path)
