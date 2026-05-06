# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# collect_all ensures all C extensions and data files are bundled
pandas_datas, pandas_binaries, pandas_hiddenimports = collect_all('pandas')
plotly_datas, plotly_binaries, plotly_hiddenimports = collect_all('plotly')

a = Analysis(
    ['backend_service.py'],
    pathex=[],
    binaries=pandas_binaries + plotly_binaries,
    datas=pandas_datas + plotly_datas,
    hiddenimports=(
        pandas_hiddenimports +
        plotly_hiddenimports +
        collect_submodules('scipy') +
        collect_submodules('sklearn') +
        collect_submodules('skimage') +
        [
            'PIL',
            'PIL.Image',
            'PIL.ImageOps',
            'scipy.signal',
            'scipy.spatial',
            'scipy.ndimage',
            'sklearn.utils._cython_blas',
            'sklearn.neighbors._typedefs',
            'sklearn.utils._weight_vector',
            'sklearn.utils._sorting',
            'sqlalchemy.dialects.postgresql',
            'psycopg2',
            'dotenv',
        ]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# --onedir mode: produces a folder instead of a single EXE.
# No extraction to %TEMP% on every run → Windows Defender does not
# re-scan on each launch → no more "backend did not announce port" errors.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BioLabBackend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='BioLabBackend',
)
