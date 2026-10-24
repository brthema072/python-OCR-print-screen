"""Liga as peças: atalho -> área de transferência -> OCR -> resultado."""

import threading
import time
from dataclasses import dataclass

from PIL import Image

from .area_transferencia import AreaTransferencia
from .atalhos import Atalhos
from .configuracao import (
    COPIAR_RESULTADO,
    ESPERA_CAPTURA_SEGUNDOS,
    INTERVALO_VERIFICACAO_SEGUNDOS,
)
from .ocr import MotorOcr


@dataclass(frozen=True)
class CapturaArmada:
    """Dados de uma captura que ainda está esperando a imagem.

    `frozen=True` deixa o objeto imutável. Isso ajuda quando há threads:
    depois de criado, ninguém altera os campos pela metade.
    """

    origem: str
    sequencia_base: int
    prazo: float


class MonitorCapturas:
    """Laço principal do aplicativo.

    Responsabilidades:
    - receber o aviso dos atalhos;
    - observar a área de transferência;
    - chamar o OCR e publicar o resultado.

    Os callbacks do teclado rodam em outra thread, enquanto o laço principal
    roda na thread do `main`. Por isso, o estado compartilhado (`_captura`)
    é protegido por um `threading.Lock`.
    """

    def __init__(self, motor: MotorOcr, area: AreaTransferencia) -> None:
        self._motor = motor
        self._area = area
        self._atalhos = Atalhos(self.armar)
        self._lock = threading.Lock()
        self._captura: CapturaArmada | None = None

    def armar(self, origem: str) -> None:
        """Marca o início de uma captura.

        Pode ser chamado pelos callbacks do teclado, em outra thread. O lock
        garante que o laço principal não leia um estado pela metade.
        """
        sequencia_base = self._area.sequencia()

        with self._lock:
            self._captura = CapturaArmada(
                origem=origem,
                sequencia_base=sequencia_base,
                prazo=time.monotonic() + ESPERA_CAPTURA_SEGUNDOS,
            )

        print(f"[{origem}] Aguardando a imagem na área de transferência...")

    def _captura_atual(self) -> CapturaArmada | None:
        with self._lock:
            return self._captura

    def _concluir(self, captura: CapturaArmada) -> None:
        """Desarma somente a captura que foi processada.

        Se outro atalho armou uma nova captura enquanto esta era processada,
        ela continua armada. O operador `is` compara identidade, não valores.
        """
        with self._lock:
            if self._captura is captura:
                self._captura = None

    def _cancelar_se_expirou(self) -> None:
        """Cancela a captura quando o prazo passa, avisando apenas uma vez."""
        with self._lock:
            captura = self._captura
            if captura is None or time.monotonic() < captura.prazo:
                return
            self._captura = None

        print(
            f"[{captura.origem}] Tempo esgotado aguardando a imagem. "
            "Captura cancelada."
        )

    def _processar(self, imagem: Image.Image) -> None:
        """Executa o OCR, mostra o texto e, se configurado, copia o resultado."""
        print("[OCR] Imagem recebida. Reconhecendo texto...")
        inicio = time.perf_counter()

        try:
            texto = self._motor.reconhecer(imagem)
        except Exception as erro:
            print(f"[OCR] Erro ao reconhecer a imagem: {erro}")
            return

        duracao = time.perf_counter() - inicio

        if not texto:
            print(f"[OCR] Nenhum texto encontrado ({duracao:.2f}s).")
            return

        print(f"\n--- Texto reconhecido ({duracao:.2f}s) ---")
        print(texto)
        print("--- fim ---\n")

        if not COPIAR_RESULTADO:
            return

        if self._area.copiar_texto(texto):
            print("[OCR] Texto copiado para a área de transferência.")
        else:
            print(
                "[OCR] Não foi possível copiar o texto para a "
                "área de transferência."
            )

    def executar(self) -> None:
        """Registra os atalhos e fica observando a área de transferência."""
        self._atalhos.registrar()

        print("[OCR] Atalhos ativos: Print Screen | Win+Shift+S | Ctrl+Win+S")
        print("[OCR] Pronto. Pressione Print Screen ou Win+Shift+S.")
        print("[OCR] Pressione Ctrl+C para encerrar.")

        ultima_sequencia = self._area.sequencia()

        while True:
            time.sleep(INTERVALO_VERIFICACAO_SEGUNDOS)

            self._cancelar_se_expirou()

            sequencia = self._area.sequencia()
            if sequencia == ultima_sequencia:
                continue

            ultima_sequencia = sequencia

            captura = self._captura_atual()
            if captura is None or sequencia == captura.sequencia_base:
                continue

            imagem = self._area.ler_imagem()
            if imagem is None:
                # A área de transferência mudou, mas não era uma imagem.
                # A captura continua armada até o prazo, pois o usuário pode
                # ainda estar concluindo o recorte.
                continue

            self._concluir(captura)
            self._processar(imagem)

            # O texto copiado no final do OCR também muda a sequência.
            # Atualizamos para não confundir isso com uma nova captura.
            ultima_sequencia = self._area.sequencia()
