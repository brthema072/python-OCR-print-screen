"""OCR de capturas de tela no Windows.

Atalhos:
    Print Screen    -> captura conforme a configuração do Windows
    Win + Shift + S -> ferramenta de recorte nativa do Windows
    Ctrl + Win + S  -> dispara o recorte nativo (atalho deste app)
    Alt + P         -> abre ou fecha o painel lateral de configuração

Depois que a imagem chega à área de transferência, o texto é reconhecido
pelo Tesseract (ou pelo OCR nativo do Windows, se o Tesseract não encontrar
texto), exibido no console (ou no arquivo de log do executável) e publicado
conforme as preferências do painel.

Uso:
    python app.py            # inicia em segundo plano
    python app.py --painel   # abre o painel ao iniciar

Este arquivo é só o ponto de entrada. A implementação está no pacote
`ocr_captura/`; veja `GUIA_PYTHON.md` para um passeio pelo código.
"""

import os
import sys
import threading

from ocr_captura.area_transferencia import AreaTransferencia
from ocr_captura.caminhos import arquivo_log
from ocr_captura.captura import MonitorCapturas
from ocr_captura.instancia import InstanciaUnica, avisar_instancia_existente
from ocr_captura.ocr import MotorOcr, OcrIndisponivelError
from ocr_captura.painel import PainelLateral
from ocr_captura.preferencias import GerenciadorPreferencias


def _configurar_saida() -> None:
    """Garante um destino para `print` no executável sem console.

    O PyInstaller com `--windowed` não cria console e deixa `sys.stdout` e
    `sys.stderr` como `None`. Como o restante do app usa `print` para o
    diagnóstico, redirecionamos essa saída para um arquivo de log. Se o log
    não puder ser criado, descartamos a saída em vez de derrubar o aplicativo.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return

    try:
        caminho = arquivo_log()
        caminho.parent.mkdir(parents=True, exist_ok=True)
        saida = caminho.open("a", encoding="utf-8", buffering=1)
    except OSError:
        # Falha externa (permissão, disco cheio): o app deve continuar sem
        # console em vez de morrer no primeiro print.
        saida = open(os.devnull, "w", encoding="utf-8")

    if sys.stdout is None:
        sys.stdout = saida
    if sys.stderr is None:
        sys.stderr = saida


def _executar() -> int:
    """Monta as peças do app e roda a interface até o encerramento."""
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

    # O atalho do menu Iniciar usa --painel para que o usuário veja que o app
    # abriu. O início automático com o Windows usa o modo silencioso.
    if "--painel" in sys.argv[1:]:
        painel.alternar()

    try:
        painel.executar()
    except KeyboardInterrupt:
        print("\n[OCR] Encerrando...")
    finally:
        monitor.parar()
        thread_monitor.join(timeout=1.0)

    print("[OCR] Aplicativo encerrado.")
    return 0


def main() -> int:
    """Inicia o aplicativo e devolve o código de saída do processo."""
    _configurar_saida()

    instancia = InstanciaUnica()
    if not instancia.adquirir():
        avisar_instancia_existente()
        return 0

    try:
        return _executar()
    finally:
        instancia.liberar()


if __name__ == "__main__":
    raise SystemExit(main())
