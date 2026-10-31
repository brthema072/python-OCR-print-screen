"""Reconhecimento de texto com o Tesseract e o OCR nativo do Windows.

O motor principal é o Tesseract, acessado pelo `pytesseract`. Se ele não
devolver texto, o app tenta o OCR nativo do Windows como alternativa.

O Windows expõe o OCR pelo Windows Runtime (WinRT). Essa API é assíncrona:
as operações devolvem objetos que precisam ser aguardados com `await`.
O restante do app é síncrono, então `MotorOcr` esconde essa diferença e
oferece um método simples: `reconhecer(imagem)`.
"""

import asyncio
import os
import re
import shutil
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
from types import ModuleType

from PIL import Image
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

from .configuracao import (
    CAMINHO_TESSERACT,
    IDIOMAS_OCR,
    IDIOMAS_TESSERACT,
    USAR_TESSERACT,
)
from .imagens import extrair_regioes_texto_claro, preparar_para_ocr


class OcrIndisponivelError(RuntimeError):
    """Lançado quando nem o Tesseract nem o OCR do Windows estão disponíveis."""


def _localizar_tesseract() -> str | None:
    """Devolve o caminho do executável do Tesseract, se ele existir."""
    if CAMINHO_TESSERACT:
        return CAMINHO_TESSERACT

    # shutil.which procura o programa no PATH, como o prompt de comando faz.
    caminho = shutil.which("tesseract")
    if caminho:
        return caminho

    # O instalador oficial para Windows usa esta pasta por padrão, mas nem
    # sempre a adiciona ao PATH.
    padrao = (
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Tesseract-OCR"
        / "tesseract.exe"
    )
    return str(padrao) if padrao.exists() else None


class MotorOcr:
    """Fachada síncrona para o Tesseract, com o OCR do Windows como alternativa.

    "Fachada" (facade) é um padrão de projeto: a classe esconde a
    complexidade dos dois motores e oferece uma interface pequena para o
    resto do app.
    """

    def __init__(self) -> None:
        self._engine = self._escolher_engine()
        self._tesseract, self._idiomas_tesseract = self._carregar_tesseract()

        if self._tesseract is not None:
            print(f"[OCR] Motor principal: Tesseract ({self._idiomas_tesseract})")

        if self._engine is not None:
            idioma = self._engine.recognizer_language
            papel = "Alternativa" if self._tesseract is not None else "Motor principal"
            print(f"[OCR] {papel}: OCR do Windows ({idioma.language_tag})")
        elif self._tesseract is not None:
            print("[OCR] OCR do Windows indisponível; seguindo só com o Tesseract.")

        if self._tesseract is None and self._engine is None:
            raise OcrIndisponivelError(
                "Nenhum motor de OCR está disponível.\n"
                "Instale o Tesseract-OCR (veja o README) ou um idioma de OCR "
                "do Windows em Configurações > Hora e idioma > Idioma e região."
            )

    @staticmethod
    def _escolher_engine() -> OcrEngine | None:
        """Escolhe o primeiro idioma configurado que o Windows reconhece.

        Devolve `None` quando o Windows não tem nenhum idioma de OCR
        instalado. Nesse caso, o Tesseract continua funcionando sozinho.
        """
        disponiveis = {
            idioma.language_tag.lower(): idioma
            for idioma in OcrEngine.available_recognizer_languages
        }

        for tag in IDIOMAS_OCR:
            idioma = disponiveis.get(tag.lower())
            if idioma is None:
                continue

            engine = OcrEngine.try_create_from_language(idioma)
            if engine is not None:
                return engine

        # Se nenhum idioma da lista estiver instalado, tenta o idioma do
        # perfil do usuário. O Windows pode ter OCR configurado por lá.
        return OcrEngine.try_create_from_user_profile_languages()

    @staticmethod
    def _carregar_tesseract() -> tuple[ModuleType | None, str]:
        """Importa o pytesseract e valida o executável e os idiomas.

        Devolve o módulo e a lista de idiomas realmente instalados. Se algo
        faltar, devolve `None` e desliga o Tesseract sem interromper o app.
        A validação é feita uma vez, na inicialização, para não repetir o
        custo nem as mensagens de aviso a cada captura.
        """
        if not USAR_TESSERACT:
            return None, ""

        try:
            import pytesseract
        except ImportError:
            print(
                "[OCR] pytesseract não instalado; o Tesseract não será usado. "
                "Instale com: pip install pytesseract"
            )
            return None, ""

        caminho = _localizar_tesseract()
        if caminho is None:
            print(
                "[OCR] Tesseract não encontrado; ele não será usado. "
                "Instale o Tesseract-OCR ou defina CAMINHO_TESSERACT em "
                "configuracao.py."
            )
            return None, ""

        pytesseract.pytesseract.tesseract_cmd = caminho

        try:
            instalados = set(pytesseract.get_languages(config=""))
        except (pytesseract.TesseractError, OSError) as erro:
            print(
                f"[OCR] Não foi possível executar o Tesseract em {caminho}: "
                f"{erro}\nO Tesseract não será usado."
            )
            return None, ""

        desejados = [tag for tag in IDIOMAS_TESSERACT.split("+") if tag]
        disponiveis = [tag for tag in desejados if tag in instalados]

        if not disponiveis:
            print(
                "[OCR] Nenhum idioma de IDIOMAS_TESSERACT está instalado no "
                f"Tesseract ({IDIOMAS_TESSERACT}). "
                f"Instalados: {', '.join(sorted(instalados)) or 'nenhum'}. "
                "O Tesseract não será usado."
            )
            return None, ""

        if len(disponiveis) < len(desejados):
            faltando = ", ".join(tag for tag in desejados if tag not in instalados)
            print(
                f"[OCR] Idiomas ausentes no Tesseract: {faltando}. "
                f"Usando apenas: {'+'.join(disponiveis)}"
            )

        return pytesseract, "+".join(disponiveis)

    def reconhecer(self, imagem: Image.Image) -> str:
        """Reconhece com o Tesseract e usa o OCR do Windows como alternativa."""
        preparada = preparar_para_ocr(imagem)

        texto = ""
        if self._tesseract is not None:
            texto_padrao = self._reconhecer_com_tesseract(preparada)
            texto_claro = self._reconhecer_texto_claro(imagem)
            texto, usou_mascara = self._escolher_texto(
                texto_padrao, texto_claro
            )

            if texto:
                detalhe = " (texto claro sobreposto)" if usou_mascara else ""
                print(f"[OCR] Texto recuperado pelo Tesseract{detalhe}.")
                return texto

            print(
                "[OCR] O Tesseract não encontrou texto. "
                "Tentando o OCR do Windows..."
            )

        if self._engine is None:
            return texto

        try:
            texto = asyncio.run(self._reconhecer_async(preparada))
        except Exception as erro:
            # Uma falha do WinRT (driver, memória, formato) não deve
            # derrubar o app; o resultado é tratado como "sem texto".
            print(f"[OCR] O OCR do Windows falhou: {erro}")
            return ""

        if texto:
            print("[OCR] Texto recuperado pelo OCR do Windows.")
        return texto

    def _reconhecer_com_tesseract(self, imagem: Image.Image) -> str:
        """Executa o Tesseract e devolve o texto reconhecido."""
        tesseract = self._tesseract
        if tesseract is None:
            return ""

        try:
            texto = tesseract.image_to_string(
                imagem, lang=self._idiomas_tesseract
            )
        except tesseract.TesseractError as erro:
            print(
                f"[OCR] O Tesseract não conseguiu reconhecer a imagem: {erro}\n"
                "Verifique se os idiomas configurados estão instalados "
                f"(IDIOMAS_TESSERACT = {IDIOMAS_TESSERACT!r})."
            )
            return ""
        except OSError as erro:
            # Inclui TesseractNotFoundError, quando o executável some ou o
            # caminho configurado está errado.
            print(f"[OCR] Erro ao executar o Tesseract: {erro}")
            return ""

        return texto.strip()

    def _reconhecer_texto_claro(self, imagem: Image.Image) -> str:
        """Tenta ler títulos e legendas claros que o OCR direto perdeu."""
        tesseract = self._tesseract
        if tesseract is None:
            return ""

        linhas = []
        try:
            regioes = extrair_regioes_texto_claro(imagem)
            for regiao in regioes:
                texto = tesseract.image_to_string(
                    regiao,
                    lang=self._idiomas_tesseract,
                    config="--psm 7",
                ).strip()

                # Linhas com menos de duas letras/números costumam ser ruído.
                if len(re.sub(r"\W", "", texto)) >= 2:
                    linhas.append(texto)
        except (tesseract.TesseractError, OSError, ValueError) as erro:
            print(f"[OCR] Falha ao ler texto claro sobreposto: {erro}")
            return ""

        return "\n".join(linhas)

    @staticmethod
    def _escolher_texto(padrao: str, alternativo: str) -> tuple[str, bool]:
        """Escolhe a máscara quando ela completa o resultado padrão.

        Devolve `(texto, usou_alternativo)`. A máscara só vence quando
        contém as palavras do resultado padrão (ou versões parecidas) e
        acrescenta texto. Assim, um bom resultado não é trocado por ruído.
        """
        if not padrao:
            return alternativo, bool(alternativo)
        if not alternativo:
            return padrao, False

        palavras_padrao = re.findall(r"\w+", padrao.lower())
        palavras_alternativas = re.findall(r"\w+", alternativo.lower())
        if not palavras_padrao:
            return alternativo, True

        # Palavras de uma ou duas letras costumam ser ruído do OCR
        # ("MR ae", por exemplo). Se houver palavras maiores, compare só
        # com elas; senão, use a lista inteira.
        palavras_relevantes = [
            palavra for palavra in palavras_padrao if len(palavra) >= 3
        ] or palavras_padrao

        correspondentes = sum(
            1
            for palavra in palavras_relevantes
            if any(
                SequenceMatcher(None, palavra, outra).ratio() >= 0.6
                for outra in palavras_alternativas
            )
        )
        proporcao = correspondentes / len(palavras_relevantes)
        compacto_padrao = "".join(palavras_padrao)
        compacto_alternativo = "".join(palavras_alternativas)

        if compacto_padrao in compacto_alternativo or (
            proporcao >= 0.6
            and len(compacto_alternativo) > len(compacto_padrao)
        ):
            return alternativo, True
        return padrao, False

    async def _reconhecer_async(self, imagem: Image.Image) -> str:
        """Versão assíncrona: é aqui que o `await` do WinRT acontece."""
        bitmap = await self._converter_para_bitmap(imagem)
        resultado = await self._engine.recognize_async(bitmap)

        # resultado.lines é uma coleção do WinRT. A generator expression
        # transforma cada linha no seu texto; o join junta tudo com "\n".
        return "\n".join(linha.text for linha in resultado.lines).strip()

    @staticmethod
    async def _converter_para_bitmap(imagem: Image.Image):
        """Converte uma imagem já preparada para o formato que o WinRT entende.

        O WinRT não lê `PIL.Image` diretamente. O caminho é:

            PIL.Image -> PNG em memória -> stream do WinRT -> BitmapDecoder
            -> SoftwareBitmap

        `BytesIO` é um arquivo em memória: útil para não criar arquivos
        temporários no disco.
        """
        png = BytesIO()
        imagem.save(png, format="PNG")

        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.write_bytes(png.getvalue())
        await writer.store_async()
        await writer.flush_async()
        stream.seek(0)

        decoder = await BitmapDecoder.create_async(stream)
        return await decoder.get_software_bitmap_async()
