from kivy.tools.packaging.pyinstaller_hooks import get_deps_all

kivy_deps = get_deps_all()

a = Analysis(
    ['../Regions/region_manager_app.py'],
    pathex=['..'],
    binaries=kivy_deps['binaries'],
    datas=[],
    hiddenimports=kivy_deps['hiddenimports'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=kivy_deps['excludes'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='region_manager_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)