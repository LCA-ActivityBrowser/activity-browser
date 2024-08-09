# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['run-activity-browser.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['openpyxl.cell._writer', 'PySide2.QtPrintSupport'],
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
    a.binaries,
    a.datas,
    [],
    name='Activity Browser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['activity_browser/static/icons/main/activitybrowser.ico'],
)


app = BUNDLE(exe,
    name='Activity Browser.app',
    icon='activity_browser/static/icons/main/activitybrowser.icns',
    bundle_identifier='com.cauldron',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Icon',
                'CFBundleTypeIconFile': 'activity_browser/static/icons/main/activitybrowser.icns',
                'LSItemContentTypes': ['com.cauldron'],
                'LSHandlerRank': 'Owner'
            }
        ]
    },
)
