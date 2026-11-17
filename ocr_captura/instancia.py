"""Garante que o aplicativo rode apenas uma vez por sessão do Windows.

O app registra atalhos globais e observa a área de transferência. Duas cópias
abertas ao mesmo tempo disputariam os atalhos e o clipboard. Um mutex nomeado
resolve isso: a primeira instância cria o mutex e a segunda recebe
`ERROR_ALREADY_EXISTS`.
"""

import ctypes
from ctypes import wintypes

NOME_MUTEX = "OCR-Capturas-SingleInstance"
_ERROR_ALREADY_EXISTS = 183


class InstanciaUnica:
    """Mantém um mutex nomeado enquanto o aplicativo estiver em execução."""

    def __init__(self, nome: str = NOME_MUTEX) -> None:
        self._nome = nome
        self._handle: int | None = None

    @staticmethod
    def _kernel32() -> ctypes.WinDLL:
        """Carrega a API do Windows com os tipos corretos para handles."""
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        return kernel32

    def adquirir(self) -> bool:
        """Cria o mutex e devolve False se outra instância já estiver aberta.

        Se a criação falhar por um motivo externo (por exemplo, uma política
        de segurança), o app continua: permitir duas instâncias é melhor do
        que impedir o usuário de trabalhar.
        """
        kernel32 = self._kernel32()
        handle = kernel32.CreateMutexW(None, False, self._nome)
        if not handle:
            return True

        if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False

        self._handle = handle
        return True

    def liberar(self) -> None:
        """Fecha o mutex; o Windows também o libera ao encerrar o processo."""
        if self._handle is None:
            return

        self._kernel32().CloseHandle(self._handle)
        self._handle = None


def avisar_instancia_existente() -> None:
    """Mostra um aviso curto quando o usuário abre uma segunda cópia."""
    mensagem = (
        "O OCR de Capturas já está em execução.\n\n"
        "Use Alt+P para abrir o painel de controle."
    )
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.MessageBoxW.argtypes = [
            wintypes.HWND,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.UINT,
        ]
        user32.MessageBoxW.restype = ctypes.c_int
        user32.MessageBoxW(None, mensagem, "OCR de Capturas", 0x40)
    except OSError:
        # Sem a API de interface, o terminal ou o log ainda registra o motivo.
        print("[OCR] O aplicativo já está em execução. Use Alt+P.")
