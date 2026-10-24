"""Atalhos globais de teclado e abertura da ferramenta de recorte."""

import threading
import time
from collections.abc import Callable

import keyboard

# O Windows precisa ver Win+Shift+S sem Ctrl pressionado. Se o usuário acabou
# de apertar Ctrl+Win+S, esperamos ele soltar as teclas antes de enviar o
# atalho nativo.
PAUSA_INICIAL_SEGUNDOS = 0.5
TEMPO_MAXIMO_ESPERA_SEGUNDOS = 3.0
INTERVALO_VERIFICACAO_TECLAS_SEGUNDOS = 0.05
PAUSA_ANTES_DE_ENVIAR_SEGUNDOS = 0.1


class Atalhos:
    """Registra os atalhos globais e avisa quando uma captura começa.

    `ao_armar` é uma função recebida no construtor (um callback). Assim,
    esta classe não precisa conhecer o `MonitorCapturas`: ela apenas avisa
    "um atalho foi pressionado". Isso é injeção de dependência.
    """

    def __init__(self, ao_armar: Callable[[str], None]) -> None:
        self._ao_armar = ao_armar

    def registrar(self) -> None:
        """Registra os três atalhos no Windows."""
        keyboard.add_hotkey(
            "print screen",
            lambda: self._ao_armar("Print Screen"),
        )
        keyboard.add_hotkey(
            "windows+shift+s",
            lambda: self._ao_armar("Win+Shift+S"),
        )
        keyboard.add_hotkey("ctrl+windows+s", self._ctrl_win_s)

    def _ctrl_win_s(self) -> None:
        self._ao_armar("Ctrl+Win+S")

        # O callback do teclado deve terminar rápido. A espera acontece em
        # outra thread para não travar o monitor de atalhos.
        threading.Thread(
            target=self._abrir_ferramenta_recorte,
            daemon=True,
        ).start()

    def _abrir_ferramenta_recorte(self) -> None:
        """Simula Win+Shift+S depois que o usuário solta Ctrl e Win."""
        time.sleep(PAUSA_INICIAL_SEGUNDOS)

        limite = time.monotonic() + TEMPO_MAXIMO_ESPERA_SEGUNDOS
        while time.monotonic() < limite:
            if not keyboard.is_pressed("ctrl") and not keyboard.is_pressed("windows"):
                break
            time.sleep(INTERVALO_VERIFICACAO_TECLAS_SEGUNDOS)

        time.sleep(PAUSA_ANTES_DE_ENVIAR_SEGUNDOS)
        try:
            keyboard.send("windows+shift+s")
        except Exception as erro:
            print(f"[OCR] Não foi possível abrir a ferramenta de recorte: {erro}")
