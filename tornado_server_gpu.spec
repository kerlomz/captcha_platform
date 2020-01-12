# -*- mode: python -*-
# Used to package as a single executable
# This is a configuration file

block_cipher = None

added_files = [('resource/icon.ico', 'resource'), ('resource/VERSION', 'astor')]

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
          [],
          exclude_binaries=True,
          name='captcha_platform_tornado_gpu',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          icon='resource/icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='captcha_platform_tornado_gpu')



