"""OCR de capturas de tela no Windows.

Atalhos:
    Print Screen    -> captura conforme a configuração do Windows
    Win + Shift + S -> ferramenta de recorte nativa do Windows
    Ctrl + Win + S  -> dispara o recorte nativo (atalho deste app)
    Alt + P         -> abre ou fecha o painel lateral de configuração

Depois que a imagem chega à área de transferência, o texto é reconhecido
pelo Tesseract (ou pelo OCR nativo do Windows, se o Tesseract não encontrar
texto), exibido no console e publicado conforme as preferências do painel.

Este arquivo é só o ponto de entrada. A implementação está no pacote
`ocr_captura/`; veja `GUIA_PYTHON.md` para um passeio pelo código.
"""

import sys
import threading

from ocr_captura.area_transferencia import AreaTransferencia
from ocr_captura.captura import MonitorCapturas
from ocr_captura.ocr import MotorOcr, OcrIndisponivelError
from ocr_captura.painel import PainelLateral
from ocr_captura.preferencias import GerenciadorPreferencias


def main() -> int:
    """Inicia o aplicativo e devolve o código de saída do processo."""
    try:
        motor = MotorOcr()
    except OcrIndisponivelError as erro:
        print(f"[OCR] {erro}", file=sys.stderr)
        return 1

    area = AreaTransferencia()
    preferencias = GerenciadorPreferencias()
    painel = PainelLateral(preferencias)
    monitor = MonitorCapturas(motor, area, preferencias, painel.alternar)

    # O Tkinter precisa rodar na thread principal. O monitor de capturas fica
    # em uma thread daemon e o painel recebe os pedidos por uma fila.
    thread_monitor = threading.Thread(
        target=monitor.executar,
        daemon=True,
        name="monitor-capturas",
    )
    thread_monitor.start()

    try:
        painel.executar()
    except KeyboardInterrupt:
        print("\n[OCR] Encerrando...")
    finally:
        monitor.parar()
        thread_monitor.join(timeout=1.0)

    print("[OCR] Aplicativo encerrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
