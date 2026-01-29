# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main3.0.py'],
    pathex=[],
    binaries=[],
    datas=[('de421.bsp', '.')], # Copia o arquivo BSP para a raiz do EXE
    hiddenimports=['skyfield', 'skyfield.api', 'PyQt6'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AstroControl_v3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, # Compacta o executável
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Define como False para ocultar o terminal preto ao abrir
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)