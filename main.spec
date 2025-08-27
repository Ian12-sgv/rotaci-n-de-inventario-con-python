# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['C:\\Users\\i510400\\Documents\\prueba\\python\\src'],
    binaries=[],
    datas=[],  # Sin archivos externos, dejamos datas vacía
    hiddenimports=['pyodbc', 'pandas', 'sqlalchemy'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Analisis_jessenia',  # Nombre del ejecutable; puede ser modificado según desees
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Si usas una GUI, pon console=False para ocultar la ventana de consola
    icon='assets/icon_analista.png'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main'
)
