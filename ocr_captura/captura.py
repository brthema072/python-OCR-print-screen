"""Liga as peças: atalho -> área de transferência -> OCR -> resultado."""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image

from .area_transferencia import AreaTransferencia
from .atalhos import Atalhos
from .configuracao import (
    ESPERA_CAPTURA_SEGUNDOS,
    INTERVALO_VERIFICACAO_SEGUNDOS,
    PASTA_RESULTADOS,
)
from .ocr import MotorOcr
from .preferencias import GerenciadorPreferencias


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

    Os callbacks do teclado rodam em outra thread e o laço deste monitor roda
    em uma thread daemon. Por isso, o estado compartilhado (`_captura`) é
    protegido por um `threading.Lock`, e as preferências são lidas como uma
    fotografia imutável.
    """

    def __init__(
        self,
        motor: MotorOcr,
        area: AreaTransferencia,
        preferencias: GerenciadorPreferencias,
        ao_abrir_painel: Callable[[], None],
    ) -> None:
        self._motor = motor
        self._area = area
        self._preferencias = preferencias
        self._atalhos = Atalhos(self.armar, ao_abrir_painel)
        self._lock = threading.Lock()
        self._captura: CapturaArmada | None = None
        self._parar = threading.Event()

    def armar(self, origem: str) -> None:
        """Marca o início de uma captura.

        Pode ser chamado pelos callbacks do teclado, em outra thread. O lock
        garante que o laço do monitor não leia um estado pela metade.
        """
        if not self._preferencias.atuais().ocr_ativo:
            print(
                f"[{origem}] OCR desligado. A imagem continuará disponível "
                "na área de transferência."
            )
            return

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
        """Executa o OCR e publica o resultado conforme as preferências.

        A fotografia é tirada no começo do processamento. Assim, salvar e
        copiar continuam independentes e usam o mesmo estado, mesmo que o
        usuário altere o painel enquanto o OCR roda.
        """
        preferencias = self._preferencias.atuais()

        if not preferencias.ocr_ativo:
            # Caso o OCR tenha sido desligado depois de armar a captura.
            print(
                "[OCR] OCR desligado durante a captura. A imagem foi mantida "
                "na área de transferência."
            )
            return

        print("[OCR] Imagem recebida. Reconhecendo texto...")
        inicio = time.perf_counter()

        try:
            texto = self._motor.reconhecer(imagem)
        except Exception as erro:
            # O nome da exceção aparece mesmo quando a mensagem está vazia,
            # como em um AssertionError. Sem isso, o erro fica invisível.
            print(f"[OCR] Erro ao reconhecer a imagem: {type(erro).__name__}: {erro}")
            return

        duracao = time.perf_counter() - inicio

        if not texto:
            print(f"[OCR] Nenhum texto encontrado ({duracao:.2f}s).")
            return

        print(f"\n--- Texto reconhecido ({duracao:.2f}s) ---")
        print(texto)
        print("--- fim ---\n")

        if preferencias.salvar_resultado:
            self._salvar_resultado(texto)

        if not preferencias.copiar_texto:
            return

        if self._area.copiar_texto(texto):
            print("[OCR] Texto copiado para a área de transferência.")
        else:
            print(
                "[OCR] Não foi possível copiar o texto para a "
                "área de transferência."
            )

    def _salvar_resultado(self, texto: str) -> None:
        """Salva o texto reconhecido em um arquivo .txt na pasta configurada"""
        try:
            pasta = Path(PASTA_RESULTADOS)

            if not pasta.exists():
                pasta.mkdir(parents=True, exist_ok=True)

            nome = datetime.now().strftime("ocr_%Y-%m-%d_%H-%M.txt")

            caminho = pasta / nome

            caminho.write_text(texto, encoding="utf-8")
        except OSError as erro:
            print(f"[OCR] Não foi possível salvar o texto: {erro}")
            return

        print(f"[OCR] Texto salvo em {caminho}")

    def parar(self) -> None:
        """Pede ao laço que termine na próxima verificação."""
        self._parar.set()

    def executar(self) -> None:
        """Registra os atalhos e fica observando a área de transferência."""
        self._atalhos.registrar()

        preferencias = self._preferencias.atuais()
        estado = "ligado" if preferencias.ocr_ativo else "desligado"
        print("[OCR] Atalhos ativos: Print Screen | Win+Shift+S | Ctrl+Win+S")
        print("[OCR] Painel de configuração: Alt+P")
        print(f"[OCR] OCR {estado}.")

        if preferencias.ocr_ativo:
            print("[OCR] Pronto. Pressione Print Screen ou Win+Shift+S.")
        else:
            print(
                "[OCR] Pronto. As capturas serão mantidas como imagem na "
                "área de transferência."
            )

        print("[OCR] Pressione Ctrl+C ou use o painel (Alt+P) para encerrar.")

        ultima_sequencia = self._area.sequencia()

        # Event.wait devolve True quando `parar()` é chamado e encerra o laço
        # sem esperar o intervalo inteiro.
        while not self._parar.wait(INTERVALO_VERIFICACAO_SEGUNDOS):
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
