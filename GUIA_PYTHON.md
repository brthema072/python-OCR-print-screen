# Guia rápido de Python para entender este projeto

Este guia não é um curso completo de Python. Ele explica os recursos da
linguagem que aparecem neste app e aponta onde cada um é usado. A ideia é que
você consiga abrir qualquer arquivo de `ocr_captura/` e entender o que está
acontecendo.

Se você já programa em outra linguagem, comece pela seção **O caminho de uma
captura** e depois leia os arquivos na ordem sugerida no final.

> **Se você tem só 10 minutos:** leia as seções 1, 3, 5 e 6. Elas explicam o
> fluxo, o ponto de entrada, classes/`self` e por que o estado saiu dos
> `global`. Depois abra `ocr_captura/captura.py` e tente acompanhar o método
> `executar()` linha por linha.

---

## 1. O caminho de uma captura

O app tem quatro peças principais:

```text
atalho de teclado
       |
       v
MonitorCapturas.armar()          guarda "quero capturar" + prazo
       |
       v
laço principal (a cada 80 ms)    compara a sequência do clipboard
       |
       v
AreaTransferencia.ler_imagem()   pega a imagem do clipboard
       |
       v
MotorOcr.reconhecer()            Tesseract (principal) + OCR do Windows
       |
       v
console + clipboard              mostra o texto e copia o resultado
```

O `app.py` só monta as peças:

```python
motor = MotorOcr()
area = AreaTransferencia()
monitor = MonitorCapturas(motor, area)
monitor.executar()
```

Cada classe tem uma responsabilidade. Isso é o que torna o código mais fácil
de ler: em vez de um arquivo com tudo, você pode entender uma peça por vez.

---

## 2. Módulos, pacotes e imports

Em Python, **todo arquivo `.py` é um módulo**. O arquivo
`ocr_captura/ocr.py`, por exemplo, é o módulo `ocr_captura.ocr`.

Uma pasta com um `__init__.py` é um **pacote**. É o caso de `ocr_captura/`.
O `__init__.py` pode estar vazio; neste projeto ele só tem uma docstring
explicando a estrutura.

Os imports funcionam assim:

```python
# Importa o módulo inteiro. Depois usamos Image.open, Image.new etc.
from PIL import Image

# Importa apenas uma classe/função do módulo.
from ocr_captura.ocr import MotorOcr

# Import relativo: o ponto significa "módulo irmão dentro do mesmo pacote".
from .configuracao import COPIAR_RESULTADO
```

O import relativo (`from .configuracao import ...`) só funciona dentro de um
pacote. Ele deixa claro que `configuracao.py` é uma peça interna do projeto,
não uma biblioteca externa.

Quando você roda `python app.py`, o Python coloca a pasta do `app.py` no
`sys.path`. Por isso `from ocr_captura...` funciona: o pacote está ao lado do
`app.py`.

---

## 3. O ponto de entrada: `app.py`

No fim do arquivo existe esta construção:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

- `__name__` é uma variável que o Python cria automaticamente em todo módulo.
- Quando o arquivo é executado diretamente (`python app.py`), `__name__` vale
  `"__main__"`.
- Quando o arquivo é importado por outro (`import app`), `__name__` vale
  `"app"`.

Ou seja: o bloco só executa quando o arquivo é o programa principal. Isso
permite importar funções do `app.py` em testes sem iniciar o app inteiro.

`main()` devolve um número inteiro: `0` para sucesso, `1` para erro. O
`raise SystemExit(...)` encerra o processo com esse código. É o equivalente
ao `exit code` de outras linguagens.

---

## 4. Funções e type hints

Uma função em Python usa `def`, dois-pontos e **indentação** (não chaves):

```python
def preparar_para_ocr(imagem: Image.Image) -> Image.Image:
    imagem = converter_para_rgb(imagem)
    ...
```

- `imagem: Image.Image` é um **type hint**: documenta que o parâmetro deve ser
  um objeto `Image` do Pillow.
- `-> Image.Image` documenta o tipo do retorno.
- Type hints **não são verificados em tempo de execução** por padrão. Eles
  servem para IDEs, leitura humana e ferramentas como `mypy` e Pyright.
- `Image.Image` é a classe `Image` dentro do módulo `Image` do Pillow. O
  primeiro `Image` é o módulo; o segundo, a classe.

Outros tipos que aparecem no projeto:

```python
# str = texto
def copiar_texto(self, texto: str) -> bool: ...

# "ou None" = o valor pode ser uma imagem ou None (ausência de valor).
def ler_imagem(self) -> Image.Image | None: ...

# Lista de strings, como os caminhos devolvidos pelo Explorer.
def _ler_primeira_imagem(caminhos: list[str]) -> Image.Image | None: ...

# Tupla de tamanho variável, mas todos os itens são str.
IDIOMAS_OCR: tuple[str, ...] = ("pt-BR", "pt-PT", "en-US")

# Uma função que recebe str e não devolve nada (None).
def __init__(self, ao_armar: Callable[[str], None]) -> None: ...
```

O operador `|` em tipos é o **union type**. `Image.Image | None` significa
"uma imagem ou `None`". Ele exige Python 3.10+; é por isso que o README pede
essa versão.

`None` é o "nada" do Python. É parecido com `null`/`nil` de outras linguagens,
mas é um objeto único e não um valor especial da sintaxe.

---

## 5. Classes, `self` e `@staticmethod`

Uma classe agrupa estado (atributos) e comportamento (métodos):

```python
class MotorOcr:
    def __init__(self) -> None:
        self._engine = self._escolher_engine()
```

- `__init__` é o construtor. Ele roda quando você faz `MotorOcr()`.
- `self` é a instância atual, passada explicitamente. Em Python, você escreve
  `self` no parâmetro; em outras linguagens ele é implícito (`this`).
- `self._engine` é um atributo da instância.
- O `_` no começo do nome é uma **convenção de privacidade**: significa "não
  use isso fora da classe". O Python não impede o acesso; é um acordo entre
  programadores.

`@staticmethod` cria um método que não recebe `self` e não acessa estado da
instância:

```python
class MotorOcr:
    @staticmethod
    def _escolher_engine() -> OcrEngine | None:
        ...
```

Ele é chamado como `MotorOcr._escolher_engine()` ou
`self._escolher_engine()`. Usamos quando a função é relacionada à classe, mas
não precisa de uma instância para funcionar.

### `@dataclass`

Em `captura.py`:

```python
@dataclass(frozen=True)
class CapturaArmada:
    origem: str
    sequencia_base: int
    prazo: float
```

`@dataclass` é um **decorator**. Ele gera automaticamente `__init__`,
`__repr__` e `__eq__` a partir dos campos declarados. Sem ele, você teria que
escrever manualmente:

```python
def __init__(self, origem, sequencia_base, prazo):
    self.origem = origem
    self.sequencia_base = sequencia_base
    self.prazo = prazo
```

Com `frozen=True`, o objeto fica **imutável**: tentar fazer
`captura.prazo = 10` gera um erro. Isso é útil com threads: um objeto criado
nunca muda no meio da leitura por outra thread.

### `is` versus `==`

Em `MonitorCapturas._concluir`:

```python
if self._captura is captura:
    self._captura = None
```

- `==` compara **valores** (e o `@dataclass` gera um `__eq__` que compara os
  campos).
- `is` compara **identidade**: "é exatamente o mesmo objeto na memória?".

Aqui queremos desarmar somente a captura que acabamos de processar. Se outra
captura foi armada nesse meio-tempo, ela é outro objeto e deve continuar
armada. Por isso usamos `is`.

---

## 6. Por que o estado saiu dos `global`

A versão anterior usava variáveis de módulo:

```python
_engine: OcrEngine | None = None
_armado_ate = 0.0
_sequencia_base = 0
```

e cada função precisava declarar:

```python
global _engine, _armado_ate
```

Em Python, atribuir a uma variável de módulo dentro de uma função exige
`global`. Ler não exige. Isso é uma fonte comum de bugs: é fácil esquecer o
`global` e criar uma variável local sem perceber.

No refactor:

- o motor de OCR virou o atributo `self._engine` de `MotorOcr`;
- o estado da captura virou `self._captura` de `MonitorCapturas`;
- o lock virou `self._lock` de `MonitorCapturas`.

Vantagens:

1. Fica claro quem pode alterar cada estado.
2. A classe pode ser instanciada em um teste sem contaminar o resto do app.
3. Não há `global` espalhado.
4. O estado compartilhado e o lock ficam juntos, no mesmo lugar.

Constantes como `ESPERA_CAPTURA_SEGUNDOS` continuam no módulo de configuração.
Isso é normal: constantes não mudam durante a execução.

---

## 7. Exceptions: `try`, `except`, `finally` e `raise`

Python usa exceções para erros. O padrão é:

```python
try:
    texto = self._motor.reconhecer(imagem)
except Exception as erro:
    print(f"[OCR] Erro ao reconhecer a imagem: {type(erro).__name__}: {erro}")
    return
```

- `try` contém o código que pode falhar.
- `except Tipo as nome` captura um tipo de erro e dá um nome a ele.
- `return` dentro do `except` encerra o método sem relançar o erro.

Em `ocr.py` criamos uma exceção específica:

```python
class OcrIndisponivelError(RuntimeError):
    """Lançado quando nem o Tesseract nem o OCR do Windows estão disponíveis."""
```

Ela herda de `RuntimeError`. O `app.py` captura **somente** esse tipo:

```python
try:
    motor = MotorOcr()
except OcrIndisponivelError as erro:
    print(f"[OCR] {erro}", file=sys.stderr)
    return 1
```

Isso é intencional. Erros esperados têm uma mensagem amigável; bugs
inesperados continuam mostrando o traceback, o que ajuda a diagnosticar.

O `finally` aparece em `_copiar_texto_uma_vez`:

```python
win32clipboard.OpenClipboard()
try:
    ...
finally:
    win32clipboard.CloseClipboard()
```

O `finally` executa mesmo se o código do `try` falhar. Assim o clipboard nunca
fica travado. Se `OpenClipboard()` falhar, o `try` nem começa, então não há o
que fechar.

### Capturas amplas de `Exception`

Em `AreaTransferencia.copiar_texto`, capturamos `Exception` de propósito:

```python
except Exception:
    ...
```

O `pywin32` pode lançar tipos diferentes conforme o motivo da falha. Como a
estratégia é "tentar de novo algumas vezes", não importa o tipo exato. Em
geral, capturar `Exception` é um cheiro de código ruim; aqui há um comentário
explicando a decisão.

---

## 8. `with` e context managers

O `with` garante que um recurso seja liberado no final, mesmo se ocorrer erro:

```python
with self._lock:
    self._captura = CapturaArmada(...)
```

Por baixo dos panos, o objeto do `with` implementa `__enter__` e `__exit__`.
No caso do `Lock`, `__enter__` adquire o lock e `__exit__` libera. É o mesmo
papel do `try/finally`, mas mais curto e impossível de esquecer.

Outro exemplo:

```python
with Image.open(caminho) as imagem:
    return converter_para_rgb(imagem)
```

Aqui o `with` fecha o arquivo de imagem quando o bloco termina. Repare que
`_ler_primeira_imagem` chama `converter_para_rgb(imagem).copy()` antes de
sair do `with`. Isso é necessário porque `Image.open` é **preguiçoso**: ele
pode ler os pixels do arquivo só quando alguém acessa a imagem. O `copy()`
carrega os dados em memória, então a imagem continua válida depois que o
arquivo é fechado.

---

## 9. Threads, callbacks e locks

Este app tem mais de uma thread:

- a thread principal executa `MonitorCapturas.executar()` e o laço `while`;
- a biblioteca `keyboard` executa os callbacks dos atalhos em uma thread
  interna dela;
- `Ctrl+Win+S` cria uma thread extra para esperar o usuário soltar as teclas
  antes de enviar `Win+Shift+S`.

### Callback

Um **callback** é uma função passada para outra pessoa chamar depois. Em
`captura.py`:

```python
self._atalhos = Atalhos(self.armar)
```

Estamos passando o método `armar` como valor. `Atalhos` guarda essa função e a
chama quando um atalho é pressionado:

```python
keyboard.add_hotkey("print screen", lambda: self._ao_armar("Print Screen"))
```

`self.armar` é um **bound method**: já sabe qual é o `self`, então não precisa
receber o monitor como argumento.

`lambda` cria uma função anônima de uma linha. Aqui ela é necessária porque
`add_hotkey` chama o callback sem argumentos, mas queremos passar a origem
`"Print Screen"`.

### Thread daemon

```python
threading.Thread(
    target=self._abrir_ferramenta_recorte,
    daemon=True,
).start()
```

- `target` é a função que a thread vai executar.
- `.start()` inicia a thread.
- `daemon=True` significa que essa thread não impede o programa de encerrar.
  Se o usuário fechar o app, ela morre junto.

A espera acontece em outra thread porque o callback do teclado deve terminar
rápido. Se ele dormisse 3 segundos, poderia atrasar o tratamento de outros
atalhos.

### Lock

`threading.Lock` é um cadeado: só uma thread entra no bloco por vez.

```python
with self._lock:
    captura = self._captura
    if captura is None or time.monotonic() < captura.prazo:
        return
    self._captura = None
```

Sem o lock, duas threads poderiam ler e alterar `_captura` ao mesmo tempo. Um
exemplo de problema: o laço principal decide cancelar uma captura antiga
enquanto um atalho acabou de armar uma nova; sem proteção, o cancelamento
poderia apagar a captura nova.

O CPython tem o **GIL** (Global Interpreter Lock), que faz apenas uma thread
executar bytecode por vez. Isso não dispensa o lock: o GIL não torna um
conjunto de operações atômicas, e a lógica de "ler, verificar e limpar" precisa
ser protegida como uma unidade.

---

## 10. `async` e `await`: a ponte com o WinRT

O OCR do Windows (`Windows.Media.Ocr`) é usado como alternativa quando o
Tesseract não devolve texto. Ele é uma API assíncrona: o `winrt-Python`
traduz essa API para funções `async def`, que você chama com `await`.

```python
async def _reconhecer_async(self, imagem: Image.Image) -> str:
    bitmap = await self._converter_para_bitmap(imagem)
    resultado = await self._engine.recognize_async(bitmap)
    return "\n".join(linha.text for linha in resultado.lines).strip()
```

- `async def` define uma **corrotina**. Chamar a função não executa o corpo
  imediatamente; devolve um objeto que precisa ser aguardado.
- `await` espera a operação terminar. Enquanto isso, o **event loop** pode
  executar outras tarefas assíncronas.
- O Tesseract roda de forma síncrona e é o motor principal. O `asyncio.run`
  só entra em cena quando ele não encontra texto:

```python
def reconhecer(self, imagem: Image.Image) -> str:
    preparada = preparar_para_ocr(imagem)

    if self._tesseract is not None:
        texto = self._reconhecer_com_tesseract(preparada)
        texto_claro = self._reconhecer_texto_claro(imagem)
        texto, _ = self._escolher_texto(texto, texto_claro)
        if texto:
            return texto

    if self._engine is None:
        return ""

    return asyncio.run(self._reconhecer_async(preparada))
```

A imagem preparada é reaproveitada pelos dois motores. Antes de desistir, o
Tesseract ainda tenta a máscara de texto claro (`_reconhecer_texto_claro`); se
ela contiver as mesmas palavras e acrescentar texto, `_escolher_texto` fica com
a versão da máscara.

`asyncio.run` cria o loop, executa a corrotina até o fim e fecha o loop. Ele
**bloqueia a thread principal** até o OCR terminar; nesse app isso é aceitável
porque o OCR é a tarefa atual. A vantagem é usar a API do Windows sem espalhar
`async`/`await` por todo o código.

Um detalhe importante: `async` não significa "roda em outra thread
automaticamente". Significa que a função pode pausar em pontos de `await` e
deixar o event loop fazer outra coisa. Como aqui só existe uma corrotina, o
efeito prático é sequencial.

### O caminho da imagem até o WinRT

```text
PIL.Image
   |
   | save(format="PNG") em um BytesIO
   v
bytes PNG
   |
   | DataWriter.write_bytes + await store_async/flush_async
   v
InMemoryRandomAccessStream
   |
   | await BitmapDecoder.create_async
   v
SoftwareBitmap
   |
   | await engine.recognize_async
   v
resultado.lines
```

O WinRT não aceita `PIL.Image` diretamente. Por isso existe essa conversão.
`BytesIO` é um "arquivo em memória": você escreve e lê bytes sem criar um
arquivo no disco.

---

## 11. Listas, dicionários, comprehensions e generators

### Dict comprehension

Em `_escolher_engine`:

```python
disponiveis = {
    idioma.language_tag.lower(): idioma
    for idioma in OcrEngine.available_recognizer_languages
}
```

Isso cria um dicionário no formato `{chave: valor}` percorrendo a coleção. É
equivalente a:

```python
disponiveis = {}
for idioma in OcrEngine.available_recognizer_languages:
    disponiveis[idioma.language_tag.lower()] = idioma
```

### Generator expression

Em `_reconhecer_async`:

```python
return "\n".join(linha.text for linha in resultado.lines).strip()
```

A expressão dentro do `join` é um **generator**: ela produz um item por vez,
sem criar uma lista intermediária. `join` é um método de string: ele usa o
separador (`"\n"`) para juntar todos os itens.

### `range`

```python
for tentativa in range(1, TENTATIVAS_CLIPBOARD + 1):
```

`range(1, 6)` gera `1, 2, 3, 4, 5`. O limite superior é **exclusivo**; por isso
o `+ 1` quando queremos incluir a última tentativa.

### Truthiness

Python considera alguns valores "falsos" em um `if`: `False`, `None`, `0`,
`""`, listas vazias e dicionários vazios. Por isso o código pode escrever:

```python
if not texto:
    print("Nenhum texto encontrado")
```

em vez de `if texto == ""`. Também usamos:

```python
instalados = ", ".join(...) or "nenhum"
```

Se o `join` devolver string vazia, o `or` usa `"nenhum"`.

### `isinstance`

```python
if isinstance(dados, Image.Image):
    ...
if isinstance(dados, list):
    ...
```

`isinstance` verifica o tipo em tempo de execução. É útil porque
`ImageGrab.grabclipboard()` pode devolver uma imagem, uma lista de caminhos ou
`None`.

---

## 12. Imagens com Pillow

O Pillow (`PIL`) é a biblioteca de imagens. Os pontos principais:

```python
# Modo é o formato dos pixels: RGB, RGBA (com transparência), L (cinza) etc.
if imagem.mode == "RGB":
    return imagem

# Converte para RGBA para ter um canal alfa separado.
rgba = imagem.convert("RGBA")

# Cria uma imagem branca do mesmo tamanho.
fundo = Image.new("RGB", rgba.size, (255, 255, 255))

# Cola a imagem usando o canal alfa como máscara.
fundo.paste(rgba, mask=rgba.getchannel("A"))
```

Depois, `preparar_para_ocr` amplia a imagem:

```python
fator = min(ESCALA_MAXIMA, LADO_ALVO_OCR / maior_lado)
...
return imagem.resize(novo_tamanho, Image.Resampling.LANCZOS)
```

- `min` devolve o menor valor; isso impede passar de `ESCALA_MAXIMA`.
- `round` arredonda para o inteiro mais próximo.
- `Image.Resampling.LANCZOS` é o algoritmo de reamostragem. Ele costuma dar
  bordas mais nítidas para texto do que o padrão.

Os motores de OCR trabalham melhor com uma imagem RGB sem transparência, então
`converter_para_rgb` "achata" a imagem sobre branco antes de qualquer coisa.

### Texto claro sobreposto

Títulos de vídeo e legendas costumam ser brancos ou cinzas sobre um fundo
colorido. Para esses casos, `extrair_regioes_texto_claro` calcula duas
grandezas por pixel:

```python
maior = rgb.max(axis=2)
menor = rgb.min(axis=2)
saturacao = (maior - menor) / maior
```

- `maior` é o brilho (o canal mais forte). Branco tem brilho alto.
- `saturacao` perto de 0 indica cinza/branco; perto de 1 indica cor forte.
- A máscara mantém pixels com brilho alto e saturação baixa.

Depois, o código soma a máscara nas linhas e colunas para achar faixas de
texto, recorta cada linha, amplia 4x e inverte as cores (texto preto em fundo
branco), que é o formato preferido do Tesseract. A faixa
`TEXTO_CLARO_COBERTURA_*` evita aplicar isso em capturas comuns, como uma tela
inteira branca.

---

## 13. As bibliotecas usadas pelo app

Estas bibliotecas precisam estar instaladas no ambiente virtual:

- **`win32clipboard` / `win32con`** (pacote `pywin32`): acessam a área de
  transferência. `GetClipboardSequenceNumber()` devolve um número que muda a
  cada alteração; é assim que o app detecta uma nova captura sem ficar
  comparando imagens.
- **`keyboard`**: registra atalhos globais com `add_hotkey`, verifica teclas
  com `is_pressed` e envia combinações com `send`. Ela instala um hook de
  teclado no Windows; por isso às vezes é preciso executar como administrador.
- **`pytesseract`**: ponte Python para o executável do Tesseract, o motor de
  OCR principal. Não inclui o executável nem os arquivos de idioma.
- **`numpy`**: arrays numéricos usados para calcular a máscara de texto claro
  (brilho e saturação) e localizar as linhas de texto.
- **`winrt-*`**: bindings gerados para o Windows Runtime. É o que permite
  chamar `Windows.Media.Ocr` e `Windows.Graphics.Imaging` a partir do Python.
- **`Pillow`**: manipulação de imagens e leitura do clipboard.

A maioria dessas bibliotecas usa extensões nativas (C/C++), não são Python
puro. Por isso a instalação pode variar conforme a versão do Python e do
Windows.

---

## 14. Ordem sugerida de leitura

1. **`ocr_captura/configuracao.py`** — só constantes e comentários.
2. **`ocr_captura/imagens.py`** — funções puras, fáceis de testar.
3. **`ocr_captura/area_transferencia.py`** — classes com métodos pequenos,
   retry e `try/finally`.
4. **`ocr_captura/ocr.py`** — a parte assíncrona e a conversão para WinRT.
5. **`ocr_captura/atalhos.py`** — callbacks, threads e `lambda`.
6. **`ocr_captura/captura.py`** — o laço principal, o lock e o estado.
7. **`app.py`** — a montagem final.

Ao ler, faça perguntas como:

- Qual é a entrada desta função?
- O que ela devolve?
- Ela altera algum estado compartilhado?
- O que acontece se der erro no meio?

---

## 15. Exercícios pequenos

### 1. Mudar uma configuração

Abra `ocr_captura/configuracao.py` e aumente `ESPERA_CAPTURA_SEGUNDOS` para
60. Rode o app e confirme que a mensagem de timeout demora mais.

### 2. Mostrar a origem no processamento

Hoje a mensagem é sempre `[OCR] Imagem recebida...`. Altere
`MonitorCapturas._processar` para receber também a captura e mostrar a origem:

```python
def _processar(self, captura: CapturaArmada, imagem: Image.Image) -> None:
    print(f"[{captura.origem}] Imagem recebida. Reconhecendo texto...")
```

Depois ajuste a chamada em `executar`. Isso exercita passagem de parâmetros e
uso de um `@dataclass`.

### 3. Salvar o texto em um arquivo

No final de `_processar`, antes de copiar, experimente:

```python
from pathlib import Path

Path("resultado.txt").write_text(texto, encoding="utf-8")
```

`Path` é a forma moderna de trabalhar com caminhos. `encoding="utf-8"` evita
problemas com acentos no Windows.

### 4. Testar a preparação de imagem

Instale o pytest no ambiente virtual:

```powershell
pip install pytest
```

Crie `testes/test_imagens.py`:

```python
from PIL import Image

from ocr_captura.imagens import preparar_para_ocr


def test_amplia_imagem_pequena():
    imagem = Image.new("RGB", (900, 240), "white")
    assert preparar_para_ocr(imagem).size == (1800, 480)


def test_converte_transparencia_para_rgb():
    imagem = Image.new("RGBA", (100, 100), (255, 255, 255, 0))
    assert preparar_para_ocr(imagem).mode == "RGB"
```

Rode com `pytest`. Repare que `preparar_para_ocr` não depende de Windows,
clipboard nem OCR: por isso é fácil de testar.

### 5. Trocar `print` por `logging`

Hoje o app usa `print`. Em projetos maiores, é comum usar `logging`:

```python
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.info("[OCR] Idioma: %s", idioma.display_name)
```

`logging` permite níveis (`DEBUG`, `INFO`, `WARNING`, `ERROR`), horários e
gravação em arquivo sem mudar a lógica.

### 6. Rodar ferramentas de estilo

```powershell
pip install ruff
ruff check .
ruff format .
```

`ruff` aponta imports não usados, variáveis sem uso e vários problemas de
estilo. `ruff format` formata o código automaticamente. É opcional, mas ajuda
a manter o projeto consistente.

---

## 16. Glossário rápido

| Termo | O que é neste projeto |
| --- | --- |
| **Módulo** | Um arquivo `.py`, como `ocr.py`. |
| **Pacote** | Uma pasta de módulos, como `ocr_captura/`. |
| **Função** | Bloco reutilizável; `def reconhecer(...)`. |
| **Método** | Função dentro de uma classe; recebe `self`. |
| **Classe** | Molde para criar objetos; `MotorOcr`. |
| **Instância** | Objeto criado a partir da classe; `motor = MotorOcr()`. |
| **Atributo** | Dado guardado no objeto; `self._engine`. |
| **Callback** | Função passada para ser chamada depois; `Atalhos(self.armar)`. |
| **Thread** | Linha de execução independente dentro do processo. |
| **Lock** | Cadeado que impede duas threads de entrarem no mesmo bloco. |
| **Corrotina** | Função `async def` que pode pausar em `await`. |
| **Event loop** | Laço que coordena corrotinas; criado por `asyncio.run`. |
| **Type hint** | Anotação de tipo; `imagem: Image.Image`. |
| **Dataclass** | Classe com `__init__`/`__repr__`/`__eq__` gerados. |
| **Context manager** | Objeto usado com `with`; libera recursos no final. |
| **Generator** | Sequência preguiçosa; produz um item por vez. |
| **GIL** | Lock global do CPython; não substitui um `Lock` de lógica. |
| **Clipboard** | Área de transferência do Windows. |
| **OCR** | Reconhecimento óptico de caracteres. |
| **WinRT** | Windows Runtime, API nativa usada pelo OCR. |

Se algum trecho ainda parecer mágico, uma boa técnica é isolar a função em um
arquivo de teste e imprimir os valores intermediários. Python favorece esse
tipo de experimentação: `print`, `type(valor)` e `help(função)` são ferramentas
de aprendizado.
