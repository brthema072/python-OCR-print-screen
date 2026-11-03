"""Preferências editáveis pelo painel lateral e salvas entre execuções.

As constantes de `configuracao.py` continuam sendo os valores padrão. Quando
o usuário altera uma opção no painel, a escolha vale imediatamente e é
gravada em um arquivo JSON no perfil do usuário.
"""

import json
import os
import threading
from dataclasses import dataclass, replace
from pathlib import Path

from .configuracao import (
    ARQUIVO_PREFERENCIAS,
    COPIAR_RESULTADO,
    OCR_ATIVO,
    PASTA_PREFERENCIAS,
    SALVAR_RESULTADO,
)


@dataclass(frozen=True)
class Preferencias:
    """Fotografia imutável das opções que o painel pode alterar.

    O monitor de capturas roda em outra thread. Devolver um objeto imutável
    evita que ele leia um estado pela metade enquanto o painel altera uma
    opção.
    """

    ocr_ativo: bool
    copiar_texto: bool
    salvar_resultado: bool


def _caminho_padrao() -> Path:
    """Devolve o caminho do arquivo de preferências no perfil do usuário."""
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / PASTA_PREFERENCIAS / ARQUIVO_PREFERENCIAS

    # Fallback para ambientes sem APPDATA (por exemplo, um terminal mínimo).
    return Path.home() / ".ocr_capturas" / ARQUIVO_PREFERENCIAS


class GerenciadorPreferencias:
    """Mantém as preferências em memória e as persiste em JSON.

    O lock protege a troca do objeto `Preferencias`. A leitura no laço de
    capturas é frequente, então ela é feita com uma fotografia imutável.
    """

    def __init__(self, caminho: Path | None = None) -> None:
        self._caminho = caminho or _caminho_padrao()
        self._lock = threading.Lock()
        self._preferencias = self._carregar()

    def atuais(self) -> Preferencias:
        """Devolve o estado atual sem expor o objeto interno."""
        with self._lock:
            return self._preferencias

    def definir_ocr_ativo(self, ativo: bool) -> Preferencias:
        """Liga ou desliga o OCR e salva a escolha."""
        return self._definir(ocr_ativo=ativo)

    def definir_copiar_texto(self, copiar: bool) -> Preferencias:
        """Define se o texto reconhecido substitui a imagem no clipboard."""
        return self._definir(copiar_texto=copiar)

    def definir_salvar_resultado(self, salvar: bool) -> Preferencias:
        """Define se o texto reconhecido é gravado em um arquivo .txt."""
        return self._definir(salvar_resultado=salvar)

    def _definir(self, **mudancas: bool) -> Preferencias:
        with self._lock:
            self._preferencias = replace(self._preferencias, **mudancas)
            self._salvar(self._preferencias)
            return self._preferencias

    @staticmethod
    def _padroes() -> Preferencias:
        """Monta as preferências iniciais a partir de configuracao.py."""
        return Preferencias(
            ocr_ativo=OCR_ATIVO,
            copiar_texto=COPIAR_RESULTADO,
            salvar_resultado=SALVAR_RESULTADO,
        )

    def _carregar(self) -> Preferencias:
        """Lê o JSON, usando os padrões quando o arquivo não existe ou falha."""
        padroes = self._padroes()

        try:
            dados = json.loads(self._caminho.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return padroes
        except OSError as erro:
            print(f"[OCR] Não foi possível ler as preferências: {erro}")
            return padroes
        except ValueError as erro:
            # JSON inválido é um erro esperado: o usuário pode ter editado o
            # arquivo manualmente. O app continua com os valores padrão.
            print(
                f"[OCR] Preferências inválidas em {self._caminho}: {erro}. "
                "Usando os padrões."
            )
            return padroes

        if not isinstance(dados, dict):
            print(
                f"[OCR] Preferências inválidas em {self._caminho}. "
                "Usando os padrões."
            )
            return padroes

        return Preferencias(
            ocr_ativo=self._booleano(dados, "ocr_ativo", padroes.ocr_ativo),
            copiar_texto=self._booleano(
                dados,
                "copiar_texto",
                padroes.copiar_texto,
            ),
            salvar_resultado=self._booleano(
                dados,
                "salvar_resultado",
                padroes.salvar_resultado,
            ),
        )

    @staticmethod
    def _booleano(dados: dict, chave: str, padrao: bool) -> bool:
        """Aceita apenas booleanos de verdade; ignora valores de outro tipo."""
        valor = dados.get(chave)
        return valor if isinstance(valor, bool) else padrao

    def _salvar(self, preferencias: Preferencias) -> None:
        """Grava as preferências, avisando o usuário se não for possível."""
        try:
            self._caminho.parent.mkdir(parents=True, exist_ok=True)
            dados = {
                "ocr_ativo": preferencias.ocr_ativo,
                "copiar_texto": preferencias.copiar_texto,
                "salvar_resultado": preferencias.salvar_resultado,
            }
            self._caminho.write_text(
                json.dumps(dados, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as erro:
            print(f"[OCR] Não foi possível salvar as preferências: {erro}")
