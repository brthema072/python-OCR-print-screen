"""Operações de imagem compartilhadas pelo OCR e pela área de transferência."""

from PIL import Image

from .configuracao import (
    ESCALA_MAXIMA,
    FATOR_MINIMO_DE_AMPLIACAO,
    LADO_ALVO_OCR,
)


def converter_para_rgb(imagem: Image.Image) -> Image.Image:
    """Devolve uma imagem RGB, achatando transparência sobre fundo branco.

    O OCR do Windows espera uma imagem sem canal alfa. Quando a captura tem
    transparência, colamos a imagem sobre um fundo branco para o texto
    continuar legível.

    Se a imagem já está em RGB, ela é devolvida sem cópia. Quem abriu a
    imagem de um arquivo precisa garantir que os pixels estejam carregados
    antes de fechar o arquivo (veja area_transferencia.py).
    """
    if imagem.mode == "RGB":
        return imagem

    if imagem.mode in ("RGBA", "LA", "P"):
        rgba = imagem.convert("RGBA")
        fundo = Image.new("RGB", rgba.size, (255, 255, 255))
        fundo.paste(rgba, mask=rgba.getchannel("A"))
        return fundo

    return imagem.convert("RGB")


def preparar_para_ocr(imagem: Image.Image) -> Image.Image:
    """Normaliza a imagem e amplia capturas pequenas.

    A ampliação usa a interpolação LANCZOS, que costuma preservar melhor as
    bordas das letras do que o redimensionamento padrão.
    """
    imagem = converter_para_rgb(imagem)
    maior_lado = max(imagem.size)

    if maior_lado <= 0:
        return imagem

    fator = min(ESCALA_MAXIMA, LADO_ALVO_OCR / maior_lado)
    if fator < FATOR_MINIMO_DE_AMPLIACAO:
        return imagem

    novo_tamanho = (
        round(imagem.width * fator),
        round(imagem.height * fator),
    )
    return imagem.resize(novo_tamanho, Image.Resampling.LANCZOS)
