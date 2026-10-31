"""OCR de capturas de tela no Windows.

Atalhos:
    Print Screen    -> captura conforme a configuração do Windows
    Win + Shift + S -> ferramenta de recorte nativa do Windows
    Ctrl + Win + S  -> dispara o recorte nativo (atalho deste app)

Depois que a imagem chega à área de transferência, o texto é reconhecido
pelo Tesseract (ou pelo OCR nativo do Windows, se o Tesseract não encontrar
texto), exibido no console e copiado para a área de transferência.

Este arquivo é só o ponto de entrada. A implementação está no pacote
`ocr_captura/`; veja `GUIA_PYTHON.md` para um passeio pelo código.
"""

import sys

from ocr_captura.area_transferencia import AreaTransferencia
from ocr_captura.captura import MonitorCapturas
from ocr_captura.configuracao import COPIAR_RESULTADO
from ocr_captura.ocr import MotorOcr, OcrIndisponivelError


def main() -> int:
    """Inicia o aplicativo e devolve o código de saída do processo."""
    try:
        motor = MotorOcr()
    except OcrIndisponivelError as erro:
        print(f"[OCR] {erro}", file=sys.stderr)
        return 1

    area = AreaTransferencia()
    monitor = MonitorCapturas(motor, area)

    if COPIAR_RESULTADO:
        print("[OCR] O texto reconhecido será copiado para a área de transferência.")

    try:
        monitor.executar()
    except KeyboardInterrupt:
        print("\n[OCR] Encerrando...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
