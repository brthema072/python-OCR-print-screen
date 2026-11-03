"""Painel lateral de controle, aberto e fechado com Alt+P.

O Tkinter não é seguro para acesso concorrente: todos os widgets são criados
e alterados na thread principal. O callback do atalho roda em outra thread,
então `alternar()` apenas coloca um pedido em uma fila. O laço do Tk consome
essa fila no método `_processar_fila`.

O painel não conhece OCR nem clipboard. Ele apenas lê e altera as
preferências compartilhadas.
"""

import ctypes
import queue
import signal
import tkinter as tk
from collections.abc import Callable
from types import FrameType

from .preferencias import GerenciadorPreferencias, Preferencias

LARGURA_PAINEL = 380
MARGEM_PAINEL = 22
DURACAO_ANIMACAO_MS = 180
INTERVALO_ANIMACAO_MS = 15
INTERVALO_FILA_MS = 60

LARGURA_INTERRUPTOR = 46
ALTURA_INTERRUPTOR = 26

COR_FUNDO = "#0f172a"
COR_CARD = "#1e293b"
COR_BORDA = "#334155"
COR_TEXTO = "#f8fafc"
COR_TEXTO_SUAVE = "#94a3b8"
COR_ACENTO = "#38bdf8"
COR_SUCESSO = "#34d399"
COR_ALERTA = "#f87171"
COR_DESABILITADO = "#475569"
COR_KNOB = "#f8fafc"

FONTE_TITULO = ("Segoe UI", 18, "bold")
FONTE_SUBTITULO = ("Segoe UI", 10)
FONTE_SECAO = ("Segoe UI", 9, "bold")
FONTE_TEXTO = ("Segoe UI", 10)
FONTE_TEXTO_FORTE = ("Segoe UI", 10, "bold")
FONTE_PEQUENA = ("Segoe UI", 9)
FONTE_ATALHO = ("Consolas", 9)


def _area_trabalho(root: tk.Tk) -> tuple[int, int, int, int]:
    """Devolve (esquerda, topo, direita, base) da área útil da tela.

    A área útil exclui a barra de tarefas. Se a chamada do Windows falhar,
    usamos a tela inteira como fallback.
    """
    try:
        from ctypes import wintypes

        retangulo = wintypes.RECT()
        sucesso = ctypes.windll.user32.SystemParametersInfoW(
            0x0030,  # SPI_GETWORKAREA
            0,
            ctypes.byref(retangulo),
            0,
        )
        if sucesso:
            return (
                retangulo.left,
                retangulo.top,
                retangulo.right,
                retangulo.bottom,
            )
    except (AttributeError, OSError):
        # Em sistemas sem user32 (ou em testes fora do Windows), a tela
        # inteira é um fallback aceitável.
        pass

    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


class Interruptor(tk.Canvas):
    """Interruptor desenhado no Canvas, com aparência consistente.

    O `Checkbutton` nativo do Windows não aceita bem as cores do tema. Um
    Canvas pequeno desenha o trilho e o botão e continua acessível pelo
    teclado com Espaço e Enter.
    """

    def __init__(
        self,
        master: tk.Misc,
        valor: bool,
        ao_alternar: Callable[[bool], None],
        *,
        habilitado: bool = True,
        bg: str = COR_CARD,
    ) -> None:
        super().__init__(
            master,
            width=LARGURA_INTERRUPTOR,
            height=ALTURA_INTERRUPTOR,
            bg=bg,
            highlightthickness=2,
            highlightbackground=bg,
            highlightcolor=COR_TEXTO,
            bd=0,
            cursor="hand2" if habilitado else "arrow",
            takefocus=True,
        )
        self._valor = valor
        self._habilitado = habilitado
        self._ao_alternar = ao_alternar

        self.bind("<Button-1>", self._ao_clicar)
        self.bind("<space>", self._ao_clicar)
        self.bind("<Return>", self._ao_clicar)
        self._desenhar()

    def definir(self, valor: bool, habilitado: bool = True) -> None:
        """Atualiza o desenho sem chamar o callback de alteração."""
        self._valor = valor
        self._habilitado = habilitado
        self.configure(cursor="hand2" if habilitado else "arrow")
        self._desenhar()

    def _ao_clicar(self, _evento: tk.Event) -> None:
        if not self._habilitado:
            return

        self._valor = not self._valor
        self._desenhar()
        self._ao_alternar(self._valor)

    def _desenhar(self) -> None:
        self.delete("all")

        if not self._habilitado:
            cor = COR_DESABILITADO
        elif self._valor:
            cor = COR_ACENTO
        else:
            cor = COR_DESABILITADO

        raio = ALTURA_INTERRUPTOR / 2
        self.create_oval(
            0,
            0,
            ALTURA_INTERRUPTOR,
            ALTURA_INTERRUPTOR,
            fill=cor,
            outline=cor,
        )
        self.create_oval(
            LARGURA_INTERRUPTOR - ALTURA_INTERRUPTOR,
            0,
            LARGURA_INTERRUPTOR,
            ALTURA_INTERRUPTOR,
            fill=cor,
            outline=cor,
        )
        self.create_rectangle(
            raio,
            0,
            LARGURA_INTERRUPTOR - raio,
            ALTURA_INTERRUPTOR,
            fill=cor,
            outline=cor,
        )

        margem = 3
        x = LARGURA_INTERRUPTOR - ALTURA_INTERRUPTOR + margem
        if not self._valor:
            x = margem

        self.create_oval(
            x,
            margem,
            x + ALTURA_INTERRUPTOR - 2 * margem,
            ALTURA_INTERRUPTOR - margem,
            fill=COR_KNOB,
            outline="",
        )


class PainelLateral:
    """Painel lateral que abre pela direita com animação.

    Todos os métodos que tocam no Tkinter rodam na thread principal, dentro
    de `executar()`. `alternar()` e `encerrar()` podem ser chamados de
    qualquer thread porque só escrevem na fila.
    """

    def __init__(self, preferencias: GerenciadorPreferencias) -> None:
        self._preferencias = preferencias
        self._fila: queue.Queue[str] = queue.Queue()
        self._root: tk.Tk | None = None
        self._area = (0, 0, 0, 0)
        self._aberto = False
        self._animacao: str | None = None
        self._encerramento_pedido = False

        self._interruptor_ocr: Interruptor | None = None
        self._interruptor_copiar: Interruptor | None = None
        self._interruptor_salvar: Interruptor | None = None
        self._status: tk.Label | None = None
        self._descricao_ocr: tk.Label | None = None

    def alternar(self) -> None:
        """Pede que o painel abra ou feche; seguro para qualquer thread."""
        self._fila.put("alternar")

    def encerrar(self) -> None:
        """Pede o encerramento do laço da interface."""
        self._fila.put("encerrar")

    def executar(self) -> None:
        """Cria a janela e roda o laço do Tkinter na thread atual."""
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.overrideredirect(True)
        self._root.configure(bg=COR_BORDA)
        self._root.attributes("-topmost", True)
        self._root.resizable(False, False)
        self._root.bind("<Escape>", lambda _evento: self._ocultar())

        self._area = _area_trabalho(self._root)
        self._construir()
        self._aplicar_estado(self._preferencias.atuais())

        anterior = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._ao_sinal)
        try:
            self._root.after(INTERVALO_FILA_MS, self._processar_fila)
            self._root.mainloop()
        finally:
            signal.signal(signal.SIGINT, anterior)
            self._root = None

    def _processar_fila(self) -> None:
        """Consome os pedidos vindos de outras threads."""
        if self._root is None:
            return

        if self._encerramento_pedido:
            self._root.destroy()
            return

        try:
            while True:
                evento = self._fila.get_nowait()
                if evento == "alternar":
                    self._alternar_janela()
                elif evento == "encerrar":
                    self._root.destroy()
                    return
        except queue.Empty:
            pass

        self._root.after(INTERVALO_FILA_MS, self._processar_fila)

    def _ao_sinal(self, _sinal: int, _quadro: FrameType | None) -> None:
        """Converte Ctrl+C em um pedido de encerramento para o laço do Tk.

        O handler de sinal só altera uma flag. Chamar `queue.put` aqui poderia
        travar caso o sinal chegasse no meio de uma operação da própria fila,
        porque o lock do `Queue` não é reentrante.
        """
        self._encerramento_pedido = True

    def _alternar_janela(self) -> None:
        if self._aberto:
            self._ocultar()
        else:
            self._mostrar()

    def _mostrar(self) -> None:
        if self._root is None:
            return

        self._cancelar_animacao()
        self._aberto = True

        if self._root.winfo_viewable():
            inicio = self._root.winfo_x()
        else:
            # Deixa a janela fora da tela antes de aparecer, para a animação
            # começar da borda direita.
            self._definir_x(self._x_fechado())
            self._root.deiconify()
            self._root.update_idletasks()
            inicio = self._x_fechado()

        self._root.lift()
        self._root.attributes("-topmost", True)
        self._root.focus_force()

        # manter o foco no toggle para ligar/desligar o OCR
        # if self._interruptor_ocr is not None:
        #     self._interruptor_ocr.focus_set()

        self._animar(inicio, self._x_aberto())

    def _ocultar(self) -> None:
        if self._root is None or not self._aberto:
            return

        self._aberto = False
        self._cancelar_animacao()
        self._animar(
            self._root.winfo_x(),
            self._x_fechado(),
            ao_terminar=self._finalizar_ocultacao,
        )

    def _finalizar_ocultacao(self) -> None:
        if self._root is None:
            return
        self._root.withdraw()

    def _animar(
        self,
        inicio: int,
        fim: int,
        ao_terminar: Callable[[], None] | None = None,
        passo: int = 0,
    ) -> None:
        if self._root is None:
            return

        total = max(1, DURACAO_ANIMACAO_MS // INTERVALO_ANIMACAO_MS)
        if passo >= total:
            self._definir_x(fim)
            self._animacao = None
            if ao_terminar is not None:
                ao_terminar()
            return

        progresso = passo / total
        # Ease-out cúbico: começa rápido e desacelera no final.
        suavizado = 1 - (1 - progresso) ** 3
        x = round(inicio + (fim - inicio) * suavizado)
        self._definir_x(x)

        self._animacao = self._root.after(
            INTERVALO_ANIMACAO_MS,
            lambda: self._animar(inicio, fim, ao_terminar, passo + 1),
        )

    def _cancelar_animacao(self) -> None:
        if self._animacao is not None and self._root is not None:
            self._root.after_cancel(self._animacao)
        self._animacao = None

    def _definir_x(self, x: int) -> None:
        if self._root is None:
            return

        largura, altura = self._tamanho()
        self._root.geometry(f"{largura}x{altura}+{x}+{self._area[1]}")

    def _tamanho(self) -> tuple[int, int]:
        esquerda, topo, direita, base = self._area
        largura = min(LARGURA_PAINEL, max(1, direita - esquerda))
        altura = max(1, base - topo)
        return largura, altura

    def _x_aberto(self) -> int:
        largura, _ = self._tamanho()
        return self._area[2] - largura

    def _x_fechado(self) -> int:
        return self._area[2]

    def _construir(self) -> None:
        if self._root is None:
            return

        conteudo = tk.Frame(self._root, bg=COR_FUNDO)
        conteudo.pack(fill="both", expand=True, padx=1, pady=1)

        rodape = tk.Frame(conteudo, bg=COR_FUNDO)
        rodape.pack(side="bottom", fill="x", padx=MARGEM_PAINEL, pady=(0, 18))

        corpo = tk.Frame(conteudo, bg=COR_FUNDO)
        corpo.pack(
            fill="both",
            expand=True,
            padx=MARGEM_PAINEL,
            pady=(MARGEM_PAINEL, 12),
        )

        self._construir_cabecalho(corpo)
        self._construir_cartao_ocr(corpo)
        self._construir_cartao_resultado(corpo)
        self._construir_cartao_atalhos(corpo)
        self._construir_rodape(rodape)

    def _construir_cabecalho(self, pai: tk.Misc) -> None:
        cabecalho = tk.Frame(pai, bg=COR_FUNDO)
        cabecalho.pack(fill="x")

        titulos = tk.Frame(cabecalho, bg=COR_FUNDO)
        titulos.pack(side="left", fill="x", expand=True)

        tk.Label(
            titulos,
            text="OCR de capturas",
            bg=COR_FUNDO,
            fg=COR_TEXTO,
            font=FONTE_TITULO,
        ).pack(anchor="w")

        tk.Label(
            titulos,
            text="Controle rápido",
            bg=COR_FUNDO,
            fg=COR_TEXTO_SUAVE,
            font=FONTE_SUBTITULO,
        ).pack(anchor="w", pady=(2, 0))

        tk.Button(
            cabecalho,
            text="×",
            command=self._ocultar,
            bg=COR_FUNDO,
            fg=COR_TEXTO_SUAVE,
            activebackground=COR_CARD,
            activeforeground=COR_TEXTO,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", 18),
            cursor="hand2",
            padx=6,
            pady=0,
            takefocus=0,
        ).pack(side="right", anchor="n")

    def _construir_cartao_ocr(self, pai: tk.Misc) -> None:
        cartao = self._criar_cartao(pai)

        linha = tk.Frame(cartao, bg=COR_CARD)
        linha.pack(fill="x")

        textos = tk.Frame(linha, bg=COR_CARD)
        textos.pack(side="left", fill="x", expand=True)

        tk.Label(
            textos,
            text="Reconhecer texto (OCR)",
            bg=COR_CARD,
            fg=COR_TEXTO,
            font=FONTE_TEXTO_FORTE,
        ).pack(anchor="w")

        tk.Label(
            textos,
            text="Lê o texto da imagem; o destino segue as opções abaixo.",
            bg=COR_CARD,
            fg=COR_TEXTO_SUAVE,
            font=FONTE_PEQUENA,
            wraplength=230,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        self._interruptor_ocr = Interruptor(
            linha,
            self._preferencias.atuais().ocr_ativo,
            self._ao_alternar_ocr,
            bg=COR_CARD,
        )
        self._interruptor_ocr.pack(side="right", padx=(12, 0))

        tk.Frame(cartao, bg=COR_BORDA, height=1).pack(fill="x", pady=12)

        self._status = tk.Label(
            cartao,
            text="",
            bg=COR_CARD,
            font=FONTE_PEQUENA,
        )
        self._status.pack(anchor="w")

        self._descricao_ocr = tk.Label(
            cartao,
            text="",
            bg=COR_CARD,
            fg=COR_TEXTO_SUAVE,
            font=FONTE_PEQUENA,
            wraplength=280,
            justify="left",
        )
        self._descricao_ocr.pack(anchor="w", pady=(4, 0))

    def _construir_cartao_resultado(self, pai: tk.Misc) -> None:
        self._titulo_secao(pai, "RESULTADO")
        cartao = self._criar_cartao(pai)

        self._interruptor_copiar = self._criar_linha_opcao(
            cartao,
            "Copiar texto reconhecido",
            "Substitui a imagem na área de transferência.",
            self._preferencias.atuais().copiar_texto,
            self._ao_alternar_copiar,
        )

        tk.Frame(cartao, bg=COR_BORDA, height=1).pack(fill="x", pady=12)

        self._interruptor_salvar = self._criar_linha_opcao(
            cartao,
            "Salvar histórico em .txt",
            "Grava o texto na pasta resultados_historico/.",
            self._preferencias.atuais().salvar_resultado,
            self._ao_alternar_salvar,
        )

    def _construir_cartao_atalhos(self, pai: tk.Misc) -> None:
        self._titulo_secao(pai, "ATALHOS")
        cartao = self._criar_cartao(pai)

        atalhos = (
            ("Abrir ou fechar este painel", "Alt + P"),
            ("Capturar", "Print Screen"),
            ("Recortar", "Win + Shift + S"),
            ("Recortar pelo app", "Ctrl + Win + S"),
        )

        for indice, (descricao, tecla) in enumerate(atalhos):
            if indice:
                tk.Frame(cartao, bg=COR_BORDA, height=1).pack(fill="x", pady=8)

            linha = tk.Frame(cartao, bg=COR_CARD)
            linha.pack(fill="x")

            tk.Label(
                linha,
                text=descricao,
                bg=COR_CARD,
                fg=COR_TEXTO,
                font=FONTE_PEQUENA,
            ).pack(side="left")

            tk.Label(
                linha,
                text=tecla,
                bg=COR_CARD,
                fg=COR_ACENTO,
                font=FONTE_ATALHO,
            ).pack(side="right")

    def _construir_rodape(self, rodape: tk.Frame) -> None:
        tk.Frame(rodape, bg=COR_BORDA, height=1).pack(fill="x", pady=(0, 12))

        tk.Label(
            rodape,
            text="As alterações são salvas automaticamente.\n"
            "Alt+P ou Esc fecham este painel.",
            bg=COR_FUNDO,
            fg=COR_TEXTO_SUAVE,
            font=FONTE_PEQUENA,
            justify="left",
        ).pack(anchor="w")

        tk.Button(
            rodape,
            text="Encerrar aplicativo",
            command=self.encerrar,
            bg=COR_FUNDO,
            fg=COR_TEXTO_SUAVE,
            activebackground=COR_CARD,
            activeforeground=COR_TEXTO,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=FONTE_PEQUENA,
            cursor="hand2",
            padx=0,
            pady=0,
            anchor="w",
            takefocus=0,
        ).pack(anchor="w", pady=(10, 0))

    @staticmethod
    def _titulo_secao(pai: tk.Misc, texto: str) -> None:
        tk.Label(
            pai,
            text=texto,
            bg=COR_FUNDO,
            fg=COR_TEXTO_SUAVE,
            font=FONTE_SECAO,
        ).pack(anchor="w", pady=(0, 8))

    @staticmethod
    def _criar_cartao(pai: tk.Misc) -> tk.Frame:
        cartao = tk.Frame(
            pai,
            bg=COR_CARD,
            padx=16,
            pady=14,
            highlightthickness=1,
            highlightbackground=COR_BORDA,
        )
        cartao.pack(fill="x", pady=(0, 18))
        return cartao

    def _criar_linha_opcao(
        self,
        pai: tk.Misc,
        titulo: str,
        descricao: str,
        valor: bool,
        ao_alternar: Callable[[bool], None],
    ) -> Interruptor:
        linha = tk.Frame(pai, bg=COR_CARD)
        linha.pack(fill="x")

        textos = tk.Frame(linha, bg=COR_CARD)
        textos.pack(side="left", fill="x", expand=True)

        tk.Label(
            textos,
            text=titulo,
            bg=COR_CARD,
            fg=COR_TEXTO,
            font=FONTE_TEXTO,
        ).pack(anchor="w")

        tk.Label(
            textos,
            text=descricao,
            bg=COR_CARD,
            fg=COR_TEXTO_SUAVE,
            font=FONTE_PEQUENA,
            wraplength=230,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        interruptor = Interruptor(
            linha,
            valor,
            ao_alternar,
            bg=COR_CARD,
        )
        interruptor.pack(side="right", padx=(12, 0))
        return interruptor

    def _ao_alternar_ocr(self, ativo: bool) -> None:
        self._preferencias.definir_ocr_ativo(ativo)
        self._aplicar_estado(self._preferencias.atuais())

    def _ao_alternar_copiar(self, copiar: bool) -> None:
        self._preferencias.definir_copiar_texto(copiar)
        self._aplicar_estado(self._preferencias.atuais())

    def _ao_alternar_salvar(self, salvar: bool) -> None:
        self._preferencias.definir_salvar_resultado(salvar)
        self._aplicar_estado(self._preferencias.atuais())

    def _aplicar_estado(self, preferencias: Preferencias) -> None:
        """Atualiza os controles e o texto de status a partir do estado."""
        if (
            self._interruptor_ocr is None
            or self._interruptor_copiar is None
            or self._interruptor_salvar is None
            or self._status is None
            or self._descricao_ocr is None
        ):
            return

        self._interruptor_ocr.definir(preferencias.ocr_ativo)
        self._interruptor_copiar.definir(
            preferencias.copiar_texto,
            habilitado=preferencias.ocr_ativo,
        )
        self._interruptor_salvar.definir(
            preferencias.salvar_resultado,
            habilitado=preferencias.ocr_ativo,
        )

        if not preferencias.ocr_ativo:
            self._status.configure(text="● OCR desligado", fg=COR_ALERTA)
            descricao = (
                "Nenhum OCR é executado. A imagem da captura continua "
                "disponível na área de transferência."
            )
        else:
            self._status.configure(text="● OCR ligado", fg=COR_SUCESSO)
            if preferencias.copiar_texto and preferencias.salvar_resultado:
                descricao = (
                    "O texto substitui a imagem e também é salvo na pasta "
                    "resultados_historico/."
                )
            elif preferencias.copiar_texto:
                descricao = (
                    "O texto reconhecido substitui a imagem na área de "
                    "transferência."
                )
            elif preferencias.salvar_resultado:
                descricao = (
                    "O texto é salvo em resultados_historico/; a imagem "
                    "continua disponível na área de transferência."
                )
            else:
                descricao = (
                    "O texto aparece apenas no console; a imagem continua "
                    "disponível na área de transferência."
                )

        self._descricao_ocr.configure(text=descricao)
