# -*- mode: python -*-

import glob
import os
import sysconfig

block_cipher = None


# The `mgrs` package (used by the recon kneeboard for MGRS coordinates) loads its
# compiled library via ctypes at runtime from ONE LEVEL ABOVE the package — i.e.
# `libmgrs.*.pyd` sits in site-packages root, not inside `mgrs/`. PyInstaller's
# import analysis (and collect_dynamic_libs) therefore never sees it, and the
# frozen app crashes on startup with "Unable to load libmgrs.cp311-win_amd64.pyd".
# Bundle it at the dist root so mgrs's `dirname(__file__)/..` lookup (and the
# default DLL search next to the exe) both find it.
_site_dirs = {sysconfig.get_paths()[k] for k in ("purelib", "platlib")}
_mgrs_binaries = [
    (lib, ".")
    for directory in _site_dirs
    for lib in glob.glob(os.path.join(directory, "libmgrs*.pyd"))
    + glob.glob(os.path.join(directory, "libmgrs*.so"))
]

analysis = Analysis(
    ['./qt_ui/main.py'],
    pathex=['.'],
    binaries=_mgrs_binaries,
    datas=[
        ('resources', 'resources'),
        ('resources/caucasus.p', 'dcs/terrain/'),
        ('resources/nevada.p', 'dcs/terrain/'),
        ('client/build', 'client/build'),
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(
    analysis.pure,
    analysis.zipped_data,
    cipher=block_cipher,
)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    icon="resources/icon.ico",
    exclude_binaries=True,
    name='retribution_main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    contents_directory='.'
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    name='dcs-retribution',
)
