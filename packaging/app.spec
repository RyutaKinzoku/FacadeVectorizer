# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — one-folder build, per docs/architecture.md §9
("prefer one-folder mode... fewer AV false positives... easier to bundle
the .onnx models and Qt plugins").

Run from anywhere (paths below are resolved relative to this spec file's
own location via PyInstaller's SPECPATH, not the invocation directory):
    pyinstaller packaging/app.spec --distpath packaging/dist --workpath packaging/build

This produces a LINUX build when run on Linux (e.g. in this dev
sandbox) and a WINDOWS build when run on Windows — PyInstaller packages
for whatever OS it's actually running on, it does not cross-compile. The
shipped, signed Windows build MUST be produced by running this exact
command on a real Windows machine (or a Windows CI runner); a Linux-built
dist/ is only useful here for validating the spec itself (data bundling,
hidden imports, exclusions) before it's ever tried on Windows for real.

excludes lists dev-only packages so a stray transitive import never pulls
test/lint/packaging tooling into the shipped bundle — defense in depth;
PyInstaller's own static analysis already only bundles what's reachable
from the entry point, so none of these should be needed in practice.
"""

from __future__ import annotations

import os

block_cipher = None

# SPECPATH is injected by PyInstaller as the directory containing this
# spec file (packaging/) — paths here are resolved relative to it, NOT
# relative to wherever `pyinstaller` was invoked from. Computing the
# project root from it is what makes this spec runnable from any cwd.
PROJECT_ROOT = os.path.dirname(SPECPATH)  # noqa: F821

a = Analysis(
    [os.path.join(PROJECT_ROOT, "src", "app", "main.py")],
    pathex=[os.path.join(PROJECT_ROOT, "src")],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, "i18n"), "i18n"),
        (os.path.join(PROJECT_ROOT, "models"), "models"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "pytest_qt",
        "ruff",
        "mypy",
        "pip_tools",
        "PyInstaller",
        "torch",  # never a runtime dependency -- see requirements.in
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PhotoToCAD",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PhotoToCAD",
)
