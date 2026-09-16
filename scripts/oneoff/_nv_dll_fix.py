# -*- coding: utf-8 -*-
"""
nvidia DLL 修复: 绕过 pip, 手动下载 nvidia-*-cu12 wheel 并解压 DLL
到 onnxruntime/capi(与 onnxruntime_providers_cuda.dll 同目录, Windows DLL 搜索命中)
用法: python nv_dll_fix.py [--all]  默认只装 runtime+cublas(小), --all 连 cudnn
"""
import json
import os
import shutil
import sys
import urllib.request
import zipfile

PYPI = 'https://pypi.org/pypi/{name}/json'
PKGS = {
    'nvidia-cuda-runtime': 'bin/cudart64_13.dll',
    'nvidia-cuda-nvrtc': 'bin/nvrtc64_120_0.dll',
    'nvidia-cublas': 'bin/cublas64_13.dll',
    'nvidia-cufft': 'bin/cufft64_11.dll',
    'nvidia-curand': 'bin/curand64_10.dll',
    'nvidia-cudnn-cu13': None,   # bin 下多个 cudnn*.dll, 全部复制
}
DL_DIR = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dl'
# 沙箱限制 site-packages 写入, DLL 解到 workspace, 运行时用 os.add_dll_directory 注册
DLL_DIR = r'D:\Bonger\Desktop\2026-08-21-18-21-50\_nv_dlls'


def get_url(name, ver=None):
    with urllib.request.urlopen(PYPI.format(name=name), timeout=60) as r:
        data = json.load(r)
    files = data['releases'] if ver else data['urls']
    if ver:
        files = [f for f in data['releases'][ver]]
    for f in files:
        if f['filename'].endswith('py3-none-win_amd64.whl'):
            return f['filename'], f['url']
    raise RuntimeError(f'no win_amd64 wheel for {name}')


def download(name, ver=None):
    os.makedirs(DL_DIR, exist_ok=True)
    fn, url = get_url(name, ver)
    path = os.path.join(DL_DIR, fn)
    if os.path.exists(path) and os.path.getsize(path) > 1000000:
        print(f'  已存在 {fn}', flush=True)
        return path
    print(f'下载 {name} {fn} ...', flush=True)
    tmp = path + '.part'
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, 'wb') as fh:
        shutil.copyfileobj(r, fh, 1024 * 512)
    os.replace(tmp, path)
    print(f'  -> {os.path.getsize(path)/1e6:.1f} MB', flush=True)
    return path


def extract_dll(wheel, nvroot):
    """解压 wheel, 把 nvidia/**/bin/*.dll 复制到 DLL_DIR; 返回复制的 DLL 列表"""
    os.makedirs(DLL_DIR, exist_ok=True)
    with zipfile.ZipFile(wheel) as z:
        names = [n for n in z.namelist() if n.endswith('.dll')]
        for n in names:
            dll = n.split('/')[-1]
            src = z.open(n)
            dst = os.path.join(DLL_DIR, dll)
            with open(dst, 'wb') as fh, src:
                shutil.copyfileobj(src, fh, 1024 * 512)
            print(f'  + {dll}', flush=True)
        return names


def main():
    only = sys.argv[1:] or ['runtime', 'cublas', 'cufft', 'curand']
    names = list(PKGS.keys())
    if only and '--all' not in only:
        sel = {'runtime': 'nvidia-cuda-runtime', 'nvrtc': 'nvidia-cuda-nvrtc',
               'cublas': 'nvidia-cublas',
               'cufft': 'nvidia-cufft', 'curand': 'nvidia-curand',
               'cudnn': 'nvidia-cudnn-cu13'}
        names = [sel[k] for k in only if k in sel]
    nvroot = os.path.join(DL_DIR, 'nv')
    for name in names:
        try:
            ver = None
            if name == 'nvidia-cublas':
                ver = '13.3.0.5'       # 匹配驱动 UMD 13.3, 13.6 需要更新驱动
            elif name == 'nvidia-cudnn-cu13':
                ver = '9.15.0.57'
            wheel = download(name, ver)
            extract_dll(wheel, nvroot)
        except Exception as e:
            print(f'!! {name} 失败: {e}', flush=True)
    print('完成')


if __name__ == '__main__':
    main()
