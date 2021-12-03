# -*- mode: python -*-
# Used to package as a single executable
# This is a configuration file
import cv2
import os
from PyInstaller.utils.hooks import collect_all


block_cipher = None

binaries, hiddenimports = [], ['numpy.core._dtype_ctypes']
tmp_ret = collect_all('tzdata')
added_files = [('resource/icon.ico', 'resource'), ('resource/favorite.ico', '.'), ('resource/VERSION', 'astor'), ('resource/VERSION', '.')]
added_files += tmp_ret[0]; binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(['tornado_server.py'],
             pathex=['.', os.path.join(os.path.dirname(cv2.__file__), 'config-3.9')],
             binaries=binaries,
             datas=added_files,
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='captcha_platform_tornado',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True,
          icon='resource/icon.ico')
