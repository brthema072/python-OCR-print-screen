"""Reconhecimento de texto com o OCR nativo do Windows.

O Windows expõe o OCR pelo Windows Runtime (WinRT). Essa API é assíncrona:
as operações devolvem objetos que precisam ser aguardados com `await`.
O restante do app é síncrono, então `MotorOcr` esconde essa diferença e
oferece um método simples: `reconhecer(imagem)`.
"""

import asyncio
from io import BytesIO

from PIL import Image
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

from .configuracao import IDIOMAS_OCR
from .imagens import preparar_para_ocr


class OcrIndisponivelError(RuntimeError):
    """Lançado quando o Windows não tem nenhum idioma de OCR instalado."""


class MotorOcr:
    """Fachada síncrona para o motor de OCR do Windows.

    "Fachada" (facade) é um padrão de projeto: a classe esconde a
    complexidade do WinRT e oferece uma interface pequena para o resto do app.
    """

    def __init__(self) -> None:
        self._engine = self._escolher_engine()
        idioma = self._engine.recognizer_language
        print(f"[OCR] Idioma: {idioma.display_name} ({idioma.language_tag})")

    @staticmethod
    def _escolher_engine() -> OcrEngine:
        """Escolhe o primeiro idioma configurado que o Windows reconhece."""
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
        engine = OcrEngine.try_create_from_user_profile_languages()
        if engine is not None:
            return engine

        instalados = (
            ", ".join(i.language_tag for i in OcrEngine.available_recognizer_languages)
            or "nenhum"
        )
        raise OcrIndisponivelError(
            "Nenhum idioma de OCR está instalado.\n"
            f"Idiomas disponíveis: {instalados}\n"
            "Instale o recurso de OCR em Configurações > Hora e idioma > "
            "Idioma e região > (idioma) > Opções de idioma."
        )

    def reconhecer(self, imagem: Image.Image) -> str:
        """Reconhece o texto e devolve as linhas separadas por quebra de linha."""
        return asyncio.run(self._reconhecer_async(imagem))

    async def _reconhecer_async(self, imagem: Image.Image) -> str:
        """Versão assíncrona: é aqui que o `await` do WinRT acontece."""
        bitmap = await self._converter_para_bitmap(imagem)
        resultado = await self._engine.recognize_async(bitmap)

        # resultado.lines é uma coleção do WinRT. A generator expression
        # transforma cada linha no seu texto; o join junta tudo com "\n".
        return "\n".join(linha.text for linha in resultado.lines).strip()

    @staticmethod
    async def _converter_para_bitmap(imagem: Image.Image):
        """Converte uma imagem do Pillow para o formato que o WinRT entende.

        O WinRT não lê `PIL.Image` diretamente. O caminho é:

            PIL.Image -> PNG em memória -> stream do WinRT -> BitmapDecoder
            -> SoftwareBitmap

        `BytesIO` é um arquivo em memória: útil para não criar arquivos
        temporários no disco.
        """
        png = BytesIO()
        preparar_para_ocr(imagem).save(png, format="PNG")

        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.write_bytes(png.getvalue())
        await writer.store_async()
        await writer.flush_async()
        stream.seek(0)

        decoder = await BitmapDecoder.create_async(stream)
        return await decoder.get_software_bitmap_async()
