# -*- mode: python ; coding: utf-8 -*-
"""Configuração do PyInstaller para o executável do OCR de Capturas.

O script `build.ps1` prepara `build/tesseract` antes de chamar este arquivo.
Copiamos o Tesseract inteiro como dados: ele é um programa externo chamado
pelo `pytesseract`, não uma biblioteca Python que o PyInstaller consiga
analisar.
"""

from pathlib import Path

RAIZ = Path(SPECPATH).resolve().parent
TESSERACT = RAIZ / "build" / "tesseract"
VERSAO_INFO = RAIZ / "build" / "version_info.txt"

if not (TESSERACT / "tesseract.exe").is_file():
    raise SystemExit(
        "Tesseract não preparado em build/tesseract. "
        "Execute empacotamento/build.ps1 em vez de chamar o PyInstaller direto."
    )

if not VERSAO_INFO.is_file():
    raise SystemExit(
        "Versão não preparada em build/version_info.txt. "
        "Execute empacotamento/build.ps1 em vez de chamar o PyInstaller direto."
    )

hiddenimports = [
    "keyboard._winkeyboard",
    "keyboard._winmouse",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.globalization",
    "winrt.windows.graphics.imaging",
    "winrt.windows.media.ocr",
    "winrt.windows.storage.streams",
]

a = Analysis(
    [str(RAIZ / "app.py")],
    pathex=[str(RAIZ)],
    binaries=[],
    datas=[(str(TESSERACT), "tesseract")],
    hiddenimports=hiddenimports,
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
    name="OCR-Capturas",
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
    contents_directory="_internal",
    icon=str(RAIZ / "empacotamento" / "ocr_capturas.ico"),
    version=str(VERSAO_INFO),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="OCR-Capturas",
)
