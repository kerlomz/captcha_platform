# -*- mode: python -*-
# Used to package as a single executable
# This is a configuration file

block_cipher = None

added_files = [('resource/icon.ico', 'resource'), ('resource/VERSION', 'astor'), ('resource/VERSION', '.')]

a = Analysis(['tornado_server.py'],
             pathex=['.'],
             binaries=[],
             datas=added_files,
             hiddenimports=['numpy.core._dtype_ctypes'],
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
