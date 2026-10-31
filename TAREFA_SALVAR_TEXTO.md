# Tarefa: salvar o texto reconhecido em um arquivo

> **Nível:** iniciante
>
> **Tempo estimado:** 30 a 45 minutos
>
> **Arquivos obrigatórios:** `ocr_captura/configuracao.py` e `ocr_captura/captura.py`
>
> **Arquivo opcional:** `README.md`

## 1. Objetivo

Hoje o app mostra o texto reconhecido no console e copia esse texto para a área
de transferência. A sua tarefa é fazer com que ele **também salve cada
resultado em um arquivo `.txt`** dentro de uma pasta `resultados/`, usando data
e hora no nome do arquivo.

O comportamento deve ser parecido com isto no console:

```text
[OCR] Texto salvo em resultados\ocr_2026-10-25_14-32-10.txt
```

E o arquivo deve conter exatamente o texto reconhecido, com acentos
preservados.

O recurso deve poder ser ligado e desligado por uma constante em
`ocr_captura/configuracao.py`:

```python
SALVAR_RESULTADO = True
```

Quando estiver `False`, o app deve continuar funcionando como hoje: mostra no
console e copia para a área de transferência, mas não grava arquivo nenhum.

> **Antes de começar:** confirme que o app já funciona com `python app.py` e
> que o OCR reconhece texto. Se ainda não funciona, siga as seções
> **Instalação** e **Problemas comuns** do `README.md` primeiro.

## 2. Por que essa tarefa é boa para aprender

Ela é pequena, mas passa por várias partes importantes do projeto:

- como uma constante de configuração chega até o código que executa a ação;
- como adicionar imports da biblioteca padrão;
- como criar um método novo dentro de uma classe existente;
- como usar `pathlib.Path` para montar caminhos;
- como usar `datetime` e `strftime` para gerar nomes com data e hora;
- como gravar texto em arquivo com `encoding="utf-8"`;
- como tratar um erro de escrita com `try/except OSError`;
- por que a posição de um `return` muda o comportamento do programa;
- como seguir o estilo do projeto: nomes em português, type hints e docstrings.

Você **não** vai mexer na parte de OCR, de imagem, de atalhos ou de clipboard.
A alteração fica no fluxo que já tem o texto final em mãos.

> O `GUIA_PYTHON.md` tem um exercício parecido (exercício 3 da seção 15). Esta
> tarefa é uma versão guiada e um pouco mais completa dele: além de salvar,
> você vai configurar a pasta, gerar um nome com data/hora e tratar erro de
> escrita.

## 3. Onde a alteração entra no fluxo

O método `MonitorCapturas._processar` já recebe a imagem, chama o OCR e obtém o
texto. Hoje ele faz, em ordem:

1. reconhece o texto;
2. mostra o texto no console;
3. copia o texto para a área de transferência, se `COPIAR_RESULTADO` for
   `True`.

A nova gravação entra **depois de mostrar o texto e antes da cópia**:

```text
_processar
    |
    +-- reconhecer texto
    |
    +-- imprimir no console
    |
    +-- se SALVAR_RESULTADO: gravar .txt     <-- NOVO
    |
    +-- se COPIAR_RESULTADO: copiar texto
```

Esse lugar é importante. O método tem este trecho:

```python
if not COPIAR_RESULTADO:
    return
```

Tudo o que estiver **depois** desse `return` não roda quando a cópia está
desligada. Se você colocar a gravação depois dele, o arquivo só será salvo
quando `COPIAR_RESULTADO` for `True`. Queremos que salvar e copiar sejam
independentes.

## 4. Mapa dos arquivos

| Arquivo | Papel no projeto | Você vai mexer? |
| --- | --- | --- |
| `ocr_captura/configuracao.py` | Constantes que ajustam o comportamento | **Sim** |
| `ocr_captura/captura.py` | Laço principal e processamento da captura | **Sim** |
| `README.md` | Documentação para quem usa o app | Opcional |
| `app.py` | Ponto de entrada; só monta as peças | Não |
| `ocr_captura/ocr.py` | Integração com o OCR do Windows | Não |
| `ocr_captura/imagens.py` | Conversão e ampliação de imagens | Não |
| `ocr_captura/area_transferencia.py` | Leitura/escrita do clipboard | Não |
| `ocr_captura/atalhos.py` | Atalhos globais de teclado | Não |

## 5. Passo a passo

### Passo 1 — adicionar as configurações

**Arquivo:** `ocr_captura/configuracao.py`

**Onde:** logo abaixo de `COPIAR_RESULTADO`.

Adicione estas duas constantes:

```python
# Se True, salva o texto reconhecido em um arquivo .txt.
SALVAR_RESULTADO = True

# Pasta onde os arquivos serão salvos. O caminho é relativo à pasta de onde
# você executa `python app.py`. A pasta é criada automaticamente.
PASTA_RESULTADOS = "resultados"
```

Repare no estilo do arquivo: nomes de constantes em MAIÚSCULAS, comentários
curtos explicando o efeito e valores simples.

`True` e `False` são os booleanos do Python. `PASTA_RESULTADOS` é uma `str`
(texto). O código que vai usar essas constantes precisa importá-las.

### Passo 2 — importar `datetime` e `Path`

**Arquivo:** `ocr_captura/captura.py`

**Onde:** no topo do arquivo, no bloco de imports.

O começo do arquivo hoje é assim:

```python
import threading
import time
from dataclasses import dataclass

from PIL import Image
```

Adicione os dois imports da biblioteca padrão depois de
`from dataclasses import dataclass`:

```python
from datetime import datetime
from pathlib import Path
```

O bloco fica assim:

```python
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image
```

- `datetime` é a classe que representa data e hora.
- `Path` é a classe do módulo `pathlib` que representa caminhos de arquivo.
- As duas fazem parte da biblioteca padrão do Python. Não é preciso instalar
  nada com `pip`.

Ainda em `captura.py`, atualize o import das configurações. Hoje ele está
assim:

```python
from .configuracao import (
    COPIAR_RESULTADO,
    ESPERA_CAPTURA_SEGUNDOS,
    INTERVALO_VERIFICACAO_SEGUNDOS,
)
```

Acrescente `PASTA_RESULTADOS` e `SALVAR_RESULTADO`:

```python
from .configuracao import (
    COPIAR_RESULTADO,
    ESPERA_CAPTURA_SEGUNDOS,
    INTERVALO_VERIFICACAO_SEGUNDOS,
    PASTA_RESULTADOS,
    SALVAR_RESULTADO,
)
```

### Passo 3 — criar o método `_salvar_resultado`

**Arquivo:** `ocr_captura/captura.py`

**Onde:** dentro da classe `MonitorCapturas`, logo depois do método
`_processar` e antes de `executar`.

A classe hoje tem esta sequência de métodos:

```python
class MonitorCapturas:
    def __init__(...): ...
    def armar(...): ...
    def _captura_atual(...): ...
    def _concluir(...): ...
    def _cancelar_se_expirou(...): ...
    def _processar(...): ...
    def executar(...): ...
```

Crie o novo método entre `_processar` e `executar`:

```python
    # <<< AQUI: novo método _salvar_resultado >>>

    def executar(self) -> None:
```

Use esta estrutura como ponto de partida. Os `...` são placeholders: você vai
trocá-los pelas expressões reais.

```python
    def _salvar_resultado(self, texto: str) -> None:
        """Salva o texto reconhecido em um arquivo .txt na pasta configurada."""
        try:
            pasta = Path(PASTA_RESULTADOS)
            # TODO: crie a pasta se ela ainda não existir.

            # TODO: monte o nome do arquivo com data e hora.
            nome = ...

            # TODO: junte a pasta e o nome em um único caminho.
            caminho = ...

            # TODO: escreva o texto no arquivo com UTF-8.
        except OSError as erro:
            print(f"[OCR] Não foi possível salvar o texto: {erro}")
            return

        print(f"[OCR] Texto salvo em {caminho}")
```

O `try` deve envolver **a criação da pasta e a escrita do arquivo**. Assim,
qualquer erro de caminho, permissão ou disco cheio cai no `except OSError`, o
app avisa e continua funcionando. O `return` dentro do `except` evita que o
`print` final tente usar um `caminho` que não foi criado.

#### Dicas para preencher os TODOs

| Você precisa... | Uma forma de fazer |
| --- | --- |
| Criar a pasta se ela não existir | `pasta.mkdir(parents=True, exist_ok=True)` |
| Gerar um nome com data e hora | `datetime.now().strftime("ocr_%Y-%m-%d_%H-%M-%S.txt")` |
| Juntar pasta e nome | `caminho = pasta / nome` |
| Gravar o texto | `caminho.write_text(texto, encoding="utf-8")` |

Entendendo cada peça:

- `pasta.mkdir(parents=True, exist_ok=True)` cria a pasta. `parents=True`
  permite criar pastas intermediárias, se necessário. `exist_ok=True` evita
  erro quando a pasta já existe (o que acontece a partir da segunda captura).
- `datetime.now()` pega a data e hora atuais. `strftime(...)` formata essa data
  como texto. Os códigos usados são: `%Y` ano, `%m` mês, `%d` dia, `%H` hora,
  `%M` minuto e `%S` segundo.
- `pasta / nome` usa o operador `/` do `Path` para juntar caminhos. O
  `pathlib` cuida do separador correto do Windows (`\`).
- `caminho.write_text(texto, encoding="utf-8")` abre o arquivo, grava o texto e
  fecha o arquivo automaticamente. `encoding="utf-8"` é o que preserva acentos
  e caracteres como `ç`, `ã` e `é`.
- `OSError` é a classe base de vários erros de arquivo, como permissão negada,
  disco cheio e caminho inválido.

> **Alternativa:** também seria possível usar `open(caminho, "w",
> encoding="utf-8")` com um bloco `with`. As duas formas funcionam.
> `write_text` é mais curto e já fecha o arquivo sozinho.

### Passo 4 — chamar o método no lugar certo

**Arquivo:** `ocr_captura/captura.py`

**Onde:** dentro de `_processar`, depois de imprimir o texto e antes de
`if not COPIAR_RESULTADO:`.

O trecho atual é este:

```python
        print(f"\n--- Texto reconhecido ({duracao:.2f}s) ---")
        print(texto)
        print("--- fim ---\n")

        if not COPIAR_RESULTADO:
            return
```

Adicione a chamada no meio:

```python
        print(f"\n--- Texto reconhecido ({duracao:.2f}s) ---")
        print(texto)
        print("--- fim ---\n")

        if SALVAR_RESULTADO:
            self._salvar_resultado(texto)

        if not COPIAR_RESULTADO:
            return
```

Não se esqueça do `self.`: `_salvar_resultado` é um método da própria classe
`MonitorCapturas`, então ele precisa ser chamado a partir da instância.

O `if SALVAR_RESULTADO:` é o que permite desligar o recurso pela configuração.
Se a constante for `False`, o método nem é chamado.

### Passo 5 (opcional) — atualizar o README

**Arquivo:** `README.md`

**Onde:** na seção `## Configurações`, junto dos outros itens.

Acrescente duas explicações:

```markdown
- `SALVAR_RESULTADO`: se `True`, salva o texto reconhecido em um arquivo
  `.txt` na pasta configurada.
- `PASTA_RESULTADOS`: pasta onde os arquivos são salvos. O caminho é relativo
  à pasta de onde o app foi executado.
```

Documentar uma configuração nova é parte de terminar bem a tarefa. Quem abrir o
projeto depois vai entender o que essas constantes fazem sem precisar ler o
código.

## 6. Como testar

### Teste 1 — o caminho feliz

1. Ative o ambiente virtual, se ainda não estiver ativo:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. Rode o app na raiz do projeto:

   ```powershell
   python app.py
   ```

3. Faça uma captura com texto. Por exemplo, abra o Bloco de Notas, escreva
   `Programação em Python é divertido` e use `Win + Shift + S` para recortar a
   frase.

4. Confira o console. Deve aparecer algo como:

   ```text
   [OCR] Texto salvo em resultados\ocr_2026-10-25_14-32-10.txt
   ```

5. Abra o arquivo em `resultados/` e confira se o texto está igual ao que
   apareceu no console, inclusive com os acentos.

6. Faça uma segunda captura e confirme que um segundo arquivo foi criado, sem
   apagar o primeiro.

### Teste 2 — desligar a gravação

1. Em `ocr_captura/configuracao.py`, mude:

   ```python
   SALVAR_RESULTADO = False
   ```

2. Rode o app e faça outra captura.

3. Confirme que **nenhum arquivo novo** apareceu em `resultados/`, mas que o
   texto continua sendo mostrado e copiado normalmente.

4. Depois volte para `True`.

### Teste 3 — salvar sem copiar

Este teste verifica se você colocou a chamada no lugar certo.

1. Configure:

   ```python
   SALVAR_RESULTADO = True
   COPIAR_RESULTADO = False
   ```

2. Rode o app e faça uma captura.

3. Confirme que o arquivo foi salvo mesmo assim. Se nada foi salvo, a chamada
   provavelmente está depois do `if not COPIAR_RESULTADO: return`.

4. Depois volte `COPIAR_RESULTADO` para `True`.

### Teste 4 (opcional) — simular um erro de gravação

1. Pare o app.
2. Se a pasta `resultados/` existir, apague-a ou renomeie.
3. Crie um **arquivo** chamado `resultados` (sem extensão) na raiz do projeto.
4. Rode o app e faça uma captura.
5. O app deve mostrar uma mensagem parecida com:

   ```text
   [OCR] Não foi possível salvar o texto: [WinError 183] ...
   ```

   E deve continuar funcionando: o texto aparece no console e é copiado.
6. Apague o arquivo `resultados` para não atrapalhar os próximos testes.

## 7. Critérios de aceite

Marque cada item depois de testar:

- [ ] Com `SALVAR_RESULTADO = True`, a pasta `resultados/` é criada
      automaticamente na primeira gravação.
- [ ] Cada OCR bem-sucedido gera um arquivo `.txt`.
- [ ] O nome do arquivo contém data e hora.
- [ ] O conteúdo do arquivo é igual ao texto mostrado no console.
- [ ] Acentos e caracteres especiais são preservados.
- [ ] O console mostra o caminho do arquivo salvo.
- [ ] Com `SALVAR_RESULTADO = False`, nenhum arquivo é criado.
- [ ] Com `COPIAR_RESULTADO = False` e `SALVAR_RESULTADO = True`, o arquivo
      ainda é salvo.
- [ ] Um erro de gravação mostra uma mensagem amigável e não impede a cópia.
- [ ] O código segue o estilo do projeto: nomes em português, type hints
      (`texto: str`, `-> None`) e docstring no método.
- [ ] Nenhuma lógica de OCR, imagem, atalho ou clipboard foi alterada.

## 8. Erros comuns e o que significam

| Mensagem ou sintoma | Causa provável | Como corrigir |
| --- | --- | --- |
| `NameError: name 'Path' is not defined` | Faltou `from pathlib import Path`. | Adicione o import no topo de `captura.py`. |
| `NameError: name 'SALVAR_RESULTADO' is not defined` | Faltou importar a constante de `configuracao.py`. | Acrescente `SALVAR_RESULTADO` ao import de `.configuracao`. |
| `FileNotFoundError` | A pasta não foi criada antes da escrita. | Use `pasta.mkdir(parents=True, exist_ok=True)` antes de `write_text`. |
| `FileExistsError` | A pasta já existe e você usou `mkdir()` sem `exist_ok=True`. | Use `exist_ok=True`. |
| Acentos viram caracteres estranhos | O arquivo foi gravado sem UTF-8. | Use `encoding="utf-8"` em `write_text`. |
| O arquivo não é salvo quando `COPIAR_RESULTADO = False` | A chamada está depois do `return` antecipado. | Mova a chamada para antes de `if not COPIAR_RESULTADO:`. |
| O arquivo aparece em outra pasta | O caminho é relativo à pasta de onde você rodou o app. | Rode `python app.py` na raiz do projeto ou use um caminho absoluto. |
| `PermissionError` | O arquivo ou a pasta está aberto em outro programa, ou o local é protegido. | Feche o arquivo/programa ou escolha outra pasta. |
| O app fecha sem mensagem | O erro não foi capturado. | Confira se `mkdir` e `write_text` estão dentro do `try`. |

## 9. Desafios extras (só depois que o básico funcionar)

### 9.1 Evitar nomes repetidos

Duas capturas no mesmo segundo podem gerar o mesmo nome de arquivo e uma
sobrescrever a outra. Acrescente microssegundos ao formato:

```python
datetime.now().strftime("ocr_%Y-%m-%d_%H-%M-%S-%f.txt")
```

`%f` são os microssegundos. O nome fica maior, mas praticamente único.

### 9.2 Salvar a pasta sempre na raiz do projeto

Hoje `PASTA_RESULTADOS` é relativo à pasta de onde você executou
`python app.py`. Se quiser que a pasta fique sempre ao lado do `app.py`,
independentemente de onde o comando foi rodado, estude estas expressões:

```python
Path(__file__).resolve().parent.parent
```

- `__file__` é o caminho do arquivo atual (`captura.py`);
- `.resolve()` transforma em caminho absoluto;
- `.parent` sobe um nível na árvore de pastas;
- dois `.parent` chegam à raiz do projeto (de `ocr_captura/captura.py` para
  `ocr_captura/` e depois para a raiz).

### 9.3 Adicionar `resultados/` ao Git

O projeto ainda não tem um `.gitignore`. Crie um na raiz com:

```gitignore
resultados/
```

Assim os arquivos gerados não aparecem como alterações no `git status`. Se
quiser, aproveite e inclua também `.venv/`.

> Os arquivos de `__pycache__/` já estão versionados neste repositório.
> Removê-los do Git é uma tarefa separada, com `git rm --cached`.

### 9.4 Salvar metadados junto do texto

Acrescente um cabeçalho ao arquivo com a origem da captura e o tempo do OCR.
Para isso, você vai precisar passar mais informações para `_processar`. O
exercício 2 do `GUIA_PYTHON.md` mostra como receber o objeto `CapturaArmada`.
É uma boa continuação depois que esta tarefa estiver funcionando.

### 9.5 Separar a geração do nome em uma função pura

Crie uma função que só devolve o nome do arquivo:

```python
def _nome_arquivo_resultado() -> str:
    ...
```

Depois use essa função em `_salvar_resultado`. Isso deixa a geração do nome
fácil de testar sem tocar no disco. É um exemplo de separar lógica pura de
efeitos colaterais.

## 10. Perguntas para se autoavaliar

Depois de terminar, tente responder sem olhar o código:

1. Por que usamos `parents=True` e `exist_ok=True` em `mkdir`?
2. Por que o `try` envolve tanto a criação da pasta quanto a escrita?
3. Por que a chamada de `_salvar_resultado` fica antes de
   `if not COPIAR_RESULTADO: return`?
4. O que acontece se `SALVAR_RESULTADO` for `False`?
5. Qual é a diferença entre `COPIAR_RESULTADO` e `SALVAR_RESULTADO`?
6. Por que `encoding="utf-8"` importa em um arquivo com acentos?
7. O que `pasta / nome` faz? Por que não precisamos nos preocupar com `\` ou
   `/`?
8. Onde o texto reconhecido é produzido? Onde ele é consumido?

Se conseguir explicar essas respostas, você entendeu não só a alteração, mas
também uma parte importante do fluxo do projeto.

## 11. Se travar

Anote e me mostre:

- o trecho que você escreveu;
- a mensagem de erro completa (copie do terminal);
- o que você esperava que acontecesse;
- o que aconteceu de fato.

Com essas informações fica fácil identificar se o problema é de import, de
caminho, de posição do código ou de sintaxe.
