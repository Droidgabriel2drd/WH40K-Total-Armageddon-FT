# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/Gabriel/Desktop/Warhammer 40k Total Armageddon/main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/Users/Gabriel/Desktop/Warhammer 40k Total Armageddon/sons', 'sons'), ('C:/Users/Gabriel/Desktop/Warhammer 40k Total Armageddon/sprites', 'sprites'), ('C:/Users/Gabriel/Desktop/Warhammer 40k Total Armageddon/musicas', 'musicas'), ('C:/Users/Gabriel/Desktop/Warhammer 40k Total Armageddon/video', 'video'), ('C:/Users/Gabriel/Desktop/Warhammer 40k Total Armageddon/menu_imperial.png', '.'), ('C:/Users/Gabriel/Desktop/Warhammer 40k Total Armageddon/menu_fundo.png', '.'), ('C:/Users/Gabriel/Desktop/Warhammer 40k Total Armageddon/icone_jogo.png', '.'), ('C:/Users/Gabriel/Desktop/Warhammer 40k Total Armageddon/config.json', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Total Armageddon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:/Users/Gabriel/Desktop/Warhammer 40k Total Armageddon/icone_jogo.ico'],
    contents_directory='.',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Total Armageddon',
)
