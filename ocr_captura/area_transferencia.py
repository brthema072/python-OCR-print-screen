"""Leitura e escrita na área de transferência do Windows."""

import time

import win32clipboard
import win32con
from PIL import Image, ImageGrab

from .configuracao import INTERVALO_TENTATIVA_SEGUNDOS, TENTATIVAS_CLIPBOARD
from .imagens import converter_para_rgb


class AreaTransferencia:
    """Operações na área de transferência com novas tentativas.

    O Windows pode deixar a área de transferência bloqueada por alguns
    milissegundos enquanto outro programa escreve nela. Por isso, as
    operações tentam novamente algumas vezes antes de desistir.
    """

    @staticmethod
    def sequencia() -> int:
        """Número que muda sempre que o conteúdo da área de transferência muda.

        Comparar esse número é muito mais barato do que comparar imagens.
        O laço principal usa essa sequência para saber quando algo mudou.
        """
        return win32clipboard.GetClipboardSequenceNumber()

    def ler_imagem(self) -> Image.Image | None:
        """Lê a área de transferência e devolve uma imagem, se houver.

        Aceita dois formatos:
        - uma imagem copiada diretamente (por exemplo, Print Screen);
        - um ou mais arquivos de imagem copiados no Explorer.
        """
        dados = self._obter_dados()

        if isinstance(dados, Image.Image):
            return converter_para_rgb(dados)

        if isinstance(dados, list):
            return self._ler_primeira_imagem(dados)

        return None

    def _obter_dados(self) -> Image.Image | list[str] | None:
        """Chama o Pillow com novas tentativas quando o clipboard está ocupado."""
        for tentativa in range(1, TENTATIVAS_CLIPBOARD + 1):
            try:
                return ImageGrab.grabclipboard()
            except OSError:
                if tentativa < TENTATIVAS_CLIPBOARD:
                    time.sleep(INTERVALO_TENTATIVA_SEGUNDOS)

        return None

    @staticmethod
    def _ler_primeira_imagem(caminhos: list[str]) -> Image.Image | None:
        """Abre o primeiro caminho que realmente for um arquivo de imagem."""
        for caminho in caminhos:
            try:
                with Image.open(caminho) as imagem:
                    # Image.open é preguiçoso: os pixels podem ser lidos do
                    # arquivo sob demanda. O copy() carrega os dados em
                    # memória antes de o `with` fechar o arquivo.
                    return converter_para_rgb(imagem).copy()
            except (OSError, ValueError):
                # Caminho inválido ou arquivo que não é imagem: tenta o próximo.
                continue

        return None

    def copiar_texto(self, texto: str) -> bool:
        """Copia texto para a área de transferência e informa se funcionou."""
        for tentativa in range(1, TENTATIVAS_CLIPBOARD + 1):
            try:
                self._copiar_texto_uma_vez(texto)
                return True
            except Exception:
                # O pywin32 pode lançar tipos de erro diferentes conforme a
                # falha. Para o usuário, o importante é tentar de novo.
                if tentativa < TENTATIVAS_CLIPBOARD:
                    time.sleep(INTERVALO_TENTATIVA_SEGUNDOS)

        return False

    @staticmethod
    def _copiar_texto_uma_vez(texto: str) -> None:
        """Faz uma única tentativa de escrita, sempre fechando o clipboard."""
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(texto, win32con.CF_UNICODETEXT)
        finally:
            # O finally executa mesmo se EmptyClipboard ou SetClipboardText
            # falhar. Sem CloseClipboard, o clipboard ficaria travado.
            win32clipboard.CloseClipboard()
