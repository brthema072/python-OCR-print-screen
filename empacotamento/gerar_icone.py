"""Gera o ícone do executável e do instalador.

O desenho usa as mesmas cores do painel lateral. O arquivo gerado,
`ocr_capturas.ico`, é incluído no PyInstaller e no Inno Setup.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

COR_FUNDO = "#0f172a"
COR_BORDA = "#334155"
COR_ACENTO = "#38bdf8"
COR_SUCESSO = "#34d399"
TAMANHOS = (16, 24, 32, 48, 64, 128, 256)


def _fonte(tamanho: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Usa a Segoe UI Bold do Windows e cai para a fonte padrão se faltar."""
    try:
        return ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", tamanho)
    except OSError:
        return ImageFont.load_default(size=tamanho)


def _desenhar(tamanho: int) -> Image.Image:
    """Desenha um quadro de captura com a sigla OCR."""
    escala = tamanho / 256
    imagem = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(imagem)

    margem = round(8 * escala)
    raio = round(52 * escala)
    desenho.rounded_rectangle(
        (margem, margem, tamanho - margem, tamanho - margem),
        radius=raio,
        fill=COR_FUNDO,
        outline=COR_BORDA,
        width=max(1, round(3 * escala)),
    )

    # Cantos de uma área de seleção de tela.
    comprimento = round(46 * escala)
    espessura = max(1, round(5 * escala))
    recuo = round(42 * escala)
    limite = tamanho - recuo
    for x, y, dx, dy in (
        (recuo, recuo, 1, 1),
        (limite, recuo, -1, 1),
        (recuo, limite, 1, -1),
        (limite, limite, -1, -1),
    ):
        desenho.line(
            (x, y, x + dx * comprimento, y),
            fill=COR_ACENTO,
            width=espessura,
        )
        desenho.line(
            (x, y, x, y + dy * comprimento),
            fill=COR_ACENTO,
            width=espessura,
        )

    fonte = _fonte(round(78 * escala))
    texto = "OCR"
    caixa = desenho.textbbox((0, 0), texto, font=fonte)
    largura = caixa[2] - caixa[0]
    altura = caixa[3] - caixa[1]
    desenho.text(
        ((tamanho - largura) / 2 - caixa[0], (tamanho - altura) / 2 - caixa[1] - 4 * escala),
        texto,
        font=fonte,
        fill=COR_SUCESSO,
    )

    return imagem


def main() -> None:
    """Gera o arquivo .ico ao lado deste script."""
    destino = Path(__file__).with_name("ocr_capturas.ico")
    imagens = [_desenhar(tamanho) for tamanho in TAMANHOS]
    imagens[-1].save(
        destino,
        format="ICO",
        append_images=imagens[:-1],
        sizes=[(tamanho, tamanho) for tamanho in TAMANHOS],
    )
    print(f"[empacotamento] Ícone gerado em {destino}")


if __name__ == "__main__":
    main()
