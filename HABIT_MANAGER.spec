# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('static', 'static'), ('app.db', '.')],
    hiddenimports=['passlib.handlers.bcrypt', 'passlib.handlers.bcrypt._bcrypt', 'passlib.handlers.pbkdf2', 'passlib.handlers.sha2_crypt', 'passlib.handlers.sha1_crypt', 'passlib.handlers.md5_crypt', 'passlib.handlers.des_crypt', 'passlib.handlers.argon2', 'bcrypt', 'bcrypt._bcrypt', 'sqlalchemy.dialects.sqlite', 'sqlalchemy.dialects.postgresql', 'sqlalchemy.sql.default_comparator', 'uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on', 'statsmodels.tsa.arima.model', 'PIL._imaging'],
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
    name='HABIT_MANAGER',
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
)
