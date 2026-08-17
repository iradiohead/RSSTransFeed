# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller definition for standalone Windows and macOS distributions."""

import sys

from PyInstaller.utils.hooks import collect_all, copy_metadata


datas = []
binaries = []
hiddenimports = []

# Argos loads translation engines and package metadata dynamically. Collecting
# the complete packages keeps model download and offline translation working in
# the frozen application.
for package in ("argostranslate", "ctranslate2", "trafilatura"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

for distribution in (
    "argostranslate",
    "ctranslate2",
    "trafilatura",
    "langdetect",
    "feedparser",
):
    datas += copy_metadata(distribution)


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RSSTransFeed",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
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
    upx_exclude=[],
    name="RSSTransFeed",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="RSSTransFeed.app",
        icon=None,
        bundle_identifier="com.rss.transfeed",
        info_plist={
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
        },
    )
