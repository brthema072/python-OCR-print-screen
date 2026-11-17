"""Caminhos de recursos e de dados do aplicativo.

O código-fonte roda a partir do projeto, mas o executável gerado pelo
PyInstaller roda a partir de outra pasta e pode estar instalado em um diretório
somente leitura. Este módulo centraliza essas diferenças para que os outros
módulos não precisem conhecer `sys.frozen` nem `sys._MEIPASS`.
"""

import os
import sys
from pathlib import Path

from .configuracao import PASTA_PREFERENCIAS, PASTA_RESULTADOS


def esta_empacotado() -> bool:
    """Indica se o código está rodando dentro de um executável PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def pasta_recursos() -> Path:
    """Pasta dos arquivos somente leitura incluídos no pacote.

    No código-fonte é a pasta do pacote `ocr_captura/`. No executável é a
    pasta `_internal` criada pelo PyInstaller (ou a pasta temporária, no modo
    `--onefile`).
    """
    if esta_empacotado():
        base = getattr(sys, "_MEIPASS", None)
        if base is not None:
            return Path(base)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def pasta_tesseract_embutido() -> Path | None:
    """Devolve o `tesseract.exe` incluído no executável, se existir.

    Também aponta `TESSDATA_PREFIX` para a pasta `tessdata` embutida. O
    Tesseract aceita a pasta pai ou a própria pasta `tessdata`, mas apontar
    para a própria pasta evita que `--list-langs` devolva nomes como
    `tessdata/eng`, que não batem com `IDIOMAS_TESSERACT`.
    """
    if not esta_empacotado():
        return None

    base = pasta_recursos() / "tesseract"
    executavel = base / "tesseract.exe"
    if not executavel.is_file():
        return None

    tessdata = base / "tessdata"
    if tessdata.is_dir():
        os.environ["TESSDATA_PREFIX"] = str(tessdata)

    return executavel


def pasta_dados_usuario() -> Path:
    """Pasta de dados do usuário, fora da pasta de instalação.

    Usa `%APPDATA%` quando disponível. O fallback `~/.ocr_capturas` atende
    ambientes mínimos, nos quais essa variável não existe.
    """
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / PASTA_PREFERENCIAS
    return Path.home() / ".ocr_capturas"


def pasta_resultados() -> Path:
    """Pasta onde o histórico de OCR é gravado.

    No código-fonte preserva a pasta relativa usada no desenvolvimento. No
    executável usa `%APPDATA%`, porque a pasta de instalação pode ser somente
    leitura e o diretório de trabalho não é controlado pelo aplicativo.
    """
    if not esta_empacotado():
        return Path(PASTA_RESULTADOS)
    return pasta_dados_usuario() / PASTA_RESULTADOS


def arquivo_log() -> Path:
    """Arquivo de log usado quando o executável não tem console."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / PASTA_PREFERENCIAS / "ocr.log"
    return pasta_dados_usuario() / "ocr.log"
