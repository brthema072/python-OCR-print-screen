"""Operações de imagem compartilhadas pelo OCR e pela área de transferência."""

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from .configuracao import (
    ESCALA_MAXIMA,
    FATOR_MINIMO_DE_AMPLIACAO,
    LADO_ALVO_OCR,
    TEXTO_CLARO_BRILHO_MINIMO,
    TEXTO_CLARO_COBERTURA_MAXIMA,
    TEXTO_CLARO_COBERTURA_MINIMA,
    TEXTO_CLARO_SATURACAO_MAXIMA,
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


def _mascara_texto_claro(imagem: Image.Image) -> np.ndarray:
    """Marca pixels claros e com pouca saturação (branco ou cinza).

    A saturação é calculada como `(maior - menor) / maior`, onde os canais
    são R, G e B. O brilho é o maior canal. Textos sobrepostos costumam ser
    brancos/cinzas: brilho alto e saturação baixa, independentemente do
    fundo colorido.
    """
    rgb = np.asarray(converter_para_rgb(imagem), dtype=np.float32) / 255.0
    maior = rgb.max(axis=2)
    menor = rgb.min(axis=2)
    saturacao = np.divide(
        maior - menor,
        maior,
        out=np.zeros_like(maior),
        where=maior > 0,
    )
    return (
        (saturacao <= TEXTO_CLARO_SATURACAO_MAXIMA)
        & (maior >= TEXTO_CLARO_BRILHO_MINIMO)
    )


def _faixas_de_linhas(mascara: np.ndarray) -> list[tuple[int, int]]:
    """Agrupa as linhas da máscara em faixas horizontais de texto."""
    fracao_minima = 0.01
    espaco_entre_linhas = 3
    margem = 4

    contagem = mascara.sum(axis=1)
    limite = max(1, int(mascara.shape[1] * fracao_minima))
    ativas = contagem >= limite

    faixas: list[tuple[int, int]] = []
    inicio = None
    ultima = None
    for y, ativa in enumerate(ativas):
        if ativa:
            if inicio is None:
                inicio = y
            ultima = y
        elif inicio is not None and y - ultima > espaco_entre_linhas:
            faixas.append((inicio, ultima))
            inicio = None
    if inicio is not None:
        faixas.append((inicio, ultima))

    return [
        (max(0, topo - margem), min(mascara.shape[0] - 1, base + margem))
        for topo, base in faixas
    ]


def _maior_grupo_de_colunas(
    faixa: np.ndarray,
) -> tuple[int, int] | None:
    """Escolhe o grupo horizontal com mais pixels de texto.

    O grupo maior costuma ser o texto; grupos pequenos nas laterais são
    ruído do fundo (microfones, refletores, etc.).
    """
    fracao_minima = 0.02
    margem = 4

    contagem = faixa.sum(axis=0)
    limite = max(1, int(faixa.shape[0] * fracao_minima))
    ativas = contagem >= limite
    espaco = max(20, faixa.shape[1] // 15)

    grupos: list[tuple[int, int]] = []
    inicio = None
    ultimo = None
    for x, ativa in enumerate(ativas):
        if ativa:
            if inicio is None:
                inicio = x
            ultimo = x
        elif inicio is not None and x - ultimo > espaco:
            grupos.append((inicio, ultimo))
            inicio = None
    if inicio is not None:
        grupos.append((inicio, ultimo))

    if not grupos:
        return None

    esquerda, direita = max(
        grupos,
        key=lambda grupo: faixa[:, grupo[0]:grupo[1] + 1].sum(),
    )
    return (
        max(0, esquerda - margem),
        min(faixa.shape[1] - 1, direita + margem),
    )


def extrair_regioes_texto_claro(imagem: Image.Image) -> list[Image.Image]:
    """Devolve recortes de linhas de texto claro sobreposto à imagem.

    Títulos de vídeo e legendas costumam ser brancos ou cinzas sobre um
    fundo com muitas cores. O OCR direto se perde no fundo; aqui isolamos
    os pixels claros e neutros, separamos as linhas e ampliamos cada uma
    com texto preto em fundo branco, que é o formato preferido do
    Tesseract.

    A lista fica vazia quando a quantidade de pixels claros não parece ser
    texto (por exemplo, uma captura com fundo branco inteiro).
    """
    mascara = _mascara_texto_claro(imagem)
    cobertura = float(mascara.mean())

    if not (
        TEXTO_CLARO_COBERTURA_MINIMA
        <= cobertura
        <= TEXTO_CLARO_COBERTURA_MAXIMA
    ):
        return []

    faixas = _faixas_de_linhas(mascara)

    # Títulos e legendas têm poucas linhas. Muitas faixas costumam ser o
    # texto normal da tela (terminal, artigo), que o OCR direto já leu.
    if len(faixas) > 4:
        return []

    regioes = []
    for topo, base in faixas:
        faixa = mascara[topo:base + 1]
        grupo = _maior_grupo_de_colunas(faixa)
        if grupo is None:
            continue

        esquerda, direita = grupo
        recorte = np.where(
            faixa[:, esquerda:direita + 1],
            0,
            255,
        ).astype(np.uint8)
        linha = Image.fromarray(recorte, mode="L")
        linha = linha.filter(ImageFilter.MedianFilter(3))
        linha = linha.resize(
            (linha.width * 4, linha.height * 4),
            Image.Resampling.LANCZOS,
        )
        regioes.append(ImageOps.expand(linha, border=40, fill=255))

    return regioes
