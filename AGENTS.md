Guia de arquitetura e de processo para agentes de IA (e pessoas) que alteram
este repositório.

**Leia antes de implementar qualquer coisa:**

- `README.md` — comportamento do app, instalação, atalhos e configurações.
- `GUIA_PYTHON.md` — conceitos de Python usados no projeto, com exemplos reais.
- Este arquivo — regras de arquitetura, estilo e processo.

O objetivo é que novas features continuem pequenas, testáveis e no módulo
certo. Preserve a estrutura existente antes de criar abstrações novas.

---

## 1. Visão geral

Aplicativo Windows que reconhece texto de capturas de tela. Os atalhos
colocam uma imagem na área de transferência; o app detecta a mudança, executa
o OCR (Tesseract como motor principal e OCR nativo do Windows como
alternativa) e publica o resultado no console ou no log, em arquivo e/ou no
clipboard. Um painel lateral aberto com `Alt+P` permite ligar/desligar o OCR e
ajustar o resultado em tempo de execução.

Requisitos de execução pelo código-fonte: Windows 10/11, Python 3.10+ e
Tesseract-OCR. O instalador e o pacote portátil não exigem Python nem
Tesseract instalados: o Tesseract vai embutido. A interface usa `tkinter`, da
biblioteca padrão.

---

## 2. Estrutura e responsabilidades

```text
app.py                          ponto de entrada; apenas monta as peças
ocr_captura/
    __init__.py                 docstring com o mapa do pacote
    configuracao.py             constantes e valores padrão ajustáveis
    caminhos.py                 recursos do executável e pastas do usuário
    preferencias.py             opções do painel, persistidas em JSON
    painel.py                   painel lateral Tkinter (Alt+P)
    imagens.py                  funções puras de imagem
    area_transferencia.py       leitura/escrita do clipboard
    ocr.py                      Tesseract + OCR do Windows
    atalhos.py                  atalhos globais de teclado
    captura.py                  laço principal, estado e publicação do resultado
    instancia.py                mutex de instância única do aplicativo
empacotamento/                  PyInstaller, Inno Setup e script de build
.github/workflows/release.yml   build e release automáticos no GitHub
requirements-dev.txt            dependências para gerar o executável
GUIA_PYTHON.md                  material didático sobre o código
README.md                       documentação para quem usa o app
```

| Módulo                  | Responsabilidade                                                                | Não deve fazer                                                          |
| ----------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `configuracao.py`       | Somente constantes e comentários.                                               | Importar módulos do projeto, executar lógica ou guardar estado mutável. |
| `caminhos.py`           | Caminhos de recursos (`sys._MEIPASS`) e dados do usuário no modo congelado.     | Acessar clipboard, OCR, Tkinter ou decidir o que salvar.                |
| `preferencias.py`       | Estado runtime imutável (`Preferencias`), lock e persistência em JSON.          | Conhecer Tkinter, OCR, clipboard ou atalhos.                            |
| `painel.py`             | Painel lateral Tkinter, animação e controles de preferência.                    | Fazer OCR, acessar clipboard ou registrar atalhos.                      |
| `imagens.py`            | Conversão para RGB, ampliação e extração de texto claro. Prefira funções puras. | Acessar clipboard, OCR, atalhos ou arquivos de resultado.               |
| `area_transferencia.py` | Ler imagens e copiar texto no clipboard, com retry.                             | Chamar OCR, registrar atalhos ou decidir o que fazer com o texto.       |
| `ocr.py`                | Fachada síncrona `MotorOcr.reconhecer(imagem)`, Tesseract e WinRT.              | Ler clipboard, registrar atalhos ou salvar resultados.                  |
| `atalhos.py`            | Registrar atalhos de captura e do painel e avisar via callback.                 | Conhecer `MonitorCapturas`, painel, OCR ou clipboard.                   |
| `captura.py`            | Orquestrar o fluxo, proteger estado compartilhado e publicar o resultado.       | Implementar detalhes de OCR, imagem, clipboard ou interface.            |
| `instancia.py`          | Mutex nomeado que impede duas cópias do app e aviso da segunda cópia.           | Conhecer OCR, captura, painel ou preferências.                          |
| `app.py`                | Composition root: criar as dependências, instância única e iniciar o app.       | Conter regra de negócio ou detalhes de implementação.                   |

### Direção das dependências

```text
app.py
  -> painel.py                 -> preferencias.py
  -> captura.py
       -> preferencias.py       -> caminhos.py -> configuracao.py
       -> ocr.py                -> caminhos.py, imagens.py, configuracao.py
       -> area_transferencia.py -> imagens.py, configuracao.py
       -> atalhos.py            (independente das demais peças)
       -> caminhos.py
  -> caminhos.py
  -> instancia.py               (independente das demais peças)
```

Regras:

1. Módulos de baixo nível não importam módulos de alto nível.
2. `captura.py` pode importar as peças internas; nenhum módulo interno importa
   `app.py`.
3. Dependências são recebidas no construtor (`MotorOcr`, `AreaTransferencia`,
   `GerenciadorPreferencias`, callbacks), não criadas escondidas dentro das
   classes.
4. Evite novos ciclos de import. Se uma feature parecer exigir um ciclo, o
   desenho das responsabilidades provavelmente está errado.
5. `painel.py` não importa `captura.py`; o atalho do painel chega por callback
   e a fila de eventos. `preferencias.py` é a única fonte compartilhada de
   opções runtime.
6. `caminhos.py` é a única fonte de caminhos de recursos e de dados do
   usuário. Não use `sys._MEIPASS`, `APPDATA` ou caminhos relativos espalhados
   pelos outros módulos; no executável, o diretório de trabalho não é
   controlado pelo app.
7. `instancia.py` não conhece o fluxo de captura; ele só cria o mutex nomeado e
   avisa quando outra cópia já está aberta.

### Fluxo de uma captura

```text
Atalhos.registrar()
  -> callback -> MonitorCapturas.armar(origem)
  -> se OCR desligado: a imagem continua no clipboard
  -> laço a cada INTERVALO_VERIFICACAO_SEGUNDOS
  -> compara a sequência do clipboard
  -> AreaTransferencia.ler_imagem()
  -> MonitorCapturas._processar()
  -> MotorOcr.reconhecer()
  -> console/log -> salvar .txt (se preferencias.salvar_resultado)
                 -> copiar texto (se preferencias.copiar_texto)

Atalhos (Alt+P)
  -> callback -> PainelLateral.alternar() -> fila
  -> thread principal (mainloop do Tk) -> GerenciadorPreferencias
```

Contratos públicos que devem permanecer estáveis:

- `MotorOcr.reconhecer(imagem) -> str`
- `AreaTransferencia.sequencia() -> int`
- `AreaTransferencia.ler_imagem() -> Image.Image | None`
- `AreaTransferencia.copiar_texto(texto) -> bool`
- `Atalhos(ao_armar, ao_abrir_painel).registrar()`
- `GerenciadorPreferencias.atuais() -> Preferencias`
- `PainelLateral.alternar()`, `PainelLateral.executar()`,
  `PainelLateral.encerrar()`
- `MonitorCapturas.executar()`, `MonitorCapturas.parar()`
- `caminhos.pasta_resultados() -> pathlib.Path`
- `caminhos.pasta_tesseract_embutido() -> pathlib.Path | None`
- `InstanciaUnica.adquirir() -> bool`

Se uma feature não couber em nenhum contrato, justifique a mudança e atualize
a documentação. Não sobrecarregue uma classe existente só para evitar criar um
módulo novo.

---

## 3. Onde cada tipo de mudança entra

| Mudança                                         | Lugar correto                       | Também atualizar                                             |
| ----------------------------------------------- | ----------------------------------- | ------------------------------------------------------------ |
| Nova constante ajustável                        | `ocr_captura/configuracao.py`       | `README.md`, seção Configurações                             |
| Nova opção alterável em runtime                 | `ocr_captura/preferencias.py`       | `painel.py`, `captura.py`, `README.md`                       |
| Controle, layout ou animação do painel          | `ocr_captura/painel.py`             | `README.md`, seção Painel lateral                            |
| Algoritmo de conversão/ampliação/máscara        | `ocr_captura/imagens.py`            | Testes, quando existirem                                     |
| Leitura/escrita do clipboard                    | `ocr_captura/area_transferencia.py` | `README.md`, se mudar o comportamento                        |
| Novo motor, idioma ou fallback de OCR           | `ocr_captura/ocr.py`                | `README.md` e `requirements.txt`, se houver dependência nova |
| Novo atalho ou mudança na ferramenta de recorte | `ocr_captura/atalhos.py`            | `README.md`, tabela de atalhos                               |
| Novo passo do fluxo, salvamento ou saída        | `ocr_captura/captura.py`            | `README.md`, fluxo e configurações                           |
| Caminho de recurso ou dado do usuário           | `ocr_captura/caminhos.py`           | `README.md`, `GUIA_PYTHON.md` e este arquivo                 |
| Instância única ou aviso de segunda cópia       | `ocr_captura/instancia.py`          | `app.py`, `empacotamento/instalador.iss`, `README.md`        |
| Inicialização, wiring ou código de saída        | `app.py`                            | Nada além do necessário                                      |
| Build, instalador, ícone ou metadados           | `empacotamento/`                    | `requirements-dev.txt`, `README.md` e este arquivo           |
| Workflow, versão ou publicação de release       | `.github/workflows/release.yml`     | `empacotamento/build.ps1`, `README.md` e este arquivo        |
| Novo conceito de Python usado no projeto        | `GUIA_PYTHON.md`                    | Exemplos devem refletir o código real                        |
| Novo módulo                                     | `ocr_captura/`                      | `__init__.py`, árvore do `README.md` e este arquivo          |

Novas dependências externas exigem atualização de `requirements.txt` e uma
justificativa no README. Não adicione bibliotecas para resolver algo que a
biblioteca padrão já resolve.

---

## 4. Convenções de código

1. **Python 3.10+**. Use type hints em funções e métodos, inclusive nos
   privados. Use `X | None` em vez de `Optional[X]`.
2. **Nomes em português**, como no restante do projeto: `reconhecer`,
   `captura`, `prazo`, `texto`. Docstrings e mensagens também em português.
3. **Classes com uma responsabilidade.** Métodos auxiliares começam com `_`.
   Constantes ficam em `configuracao.py`, em MAIÚSCULAS, com comentário curto.
4. **Sem estado global mutável.** Estado compartilhado vive em atributos de
   instância e é protegido por `threading.Lock` quando há threads.
5. **Imports**: biblioteca padrão, bibliotecas externas, depois módulos do
   projeto. Dentro do pacote, use imports relativos (`from .configuracao
import ...`).
6. **Sem efeitos colaterais no import.** Não abra clipboard, não registre
   atalhos e não inicie threads no nível do módulo.
7. **Erros esperados** recebem mensagem amigável e o app continua. Erros
   inesperados devem propagar para revelar bugs. `except Exception` só é
   aceitável quando a estratégia é explicitamente "tentar de novo" ou isolar
   uma falha externa, e isso deve estar comentado.
8. **Mensagens de console** seguem o padrão `[OCR] ...` ou `[origem] ...`.
9. **Arquivos** usam `pathlib.Path` e `encoding="utf-8"`. Erros de escrita são
   tratados como `OSError`.
10. **Threads**: callbacks de teclado devem terminar rápido. Esperas longas
    vão para uma thread `daemon`. Use `time.monotonic()` para prazos. O
    `mainloop` do Tkinter fica na thread principal; widgets nunca são tocados
    pela thread do teclado ou do monitor. Use `queue.Queue` para pedidos
    vindos de outras threads.
11. **Async**: `async`/`await` fica restrito à integração com WinRT em
    `ocr.py`. A interface pública continua síncrona; `asyncio.run` é usado na
    borda.
12. **Imutabilidade**: `CapturaArmada` e `Preferencias` são `frozen=True`; a
    remoção usa identidade (`is`), não igualdade de valores.

### Atenção ao editar `MonitorCapturas._processar`

O método lê uma fotografia de `Preferencias` no início e tem um retorno
antecipado quando `preferencias.copiar_texto` é `False`. Qualquer novo efeito
colateral (salvar arquivo, notificar, tocar som etc.) que deva ser
independente da cópia precisa entrar **antes** de:

```python
if not preferencias.copiar_texto:
    return
```

Mantenha salvar e copiar independentes. Um não deve desligar o outro. O
retorno antecipado quando `ocr_ativo` é `False` deve continuar no começo do
método, antes de qualquer OCR.

### Não faça

- Mover lógica de OCR para `captura.py` ou para `app.py`.
- Colocar código de clipboard em `ocr.py`.
- Fazer `atalhos.py` importar `captura.py` ou `painel.py`.
- Fazer `painel.py` importar `captura.py` ou tocar em widgets fora da thread
  principal.
- Trocar estado encapsulado por variáveis globais.
- Guardar opções mutáveis em `configuracao.py`; use `preferencias.py`.
- Espalhar números mágicos em vez de usar `configuracao.py`.
- Gravar resultados, preferências ou logs na pasta de instalação; use
  `caminhos.pasta_resultados()`, `pasta_dados_usuario()` e `arquivo_log()`.
- Assumir que o diretório de trabalho do executável é a pasta do projeto.
- Engolir exceções inesperadas com `except Exception: pass`.
- Alterar o formato das mensagens ou o fluxo sem atualizar README e testes.
- Commitar sem autorização explícita do usuário (veja a seção 7).

---

## 5. Checklist para novas features

Antes de codar:

- [ ] Li o README, o GUIA e os arquivos diretamente envolvidos.
- [ ] Identifiquei qual módulo é dono da responsabilidade.
- [ ] Verifiquei se o contrato público existente já resolve o caso.

Durante:

- [ ] A mudança está no módulo correto e não cria dependência invertida.
- [ ] Configurações novas estão em `configuracao.py`, com comentário.
- [ ] Type hints e docstrings foram adicionados/atualizados.
- [ ] Erros esperados têm tratamento; os inesperados continuam visíveis.
- [ ] Estado compartilhado está protegido por lock, se necessário.
- [ ] A mudança não quebra o fluxo de salvar/copiar independentes.
- [ ] Opções novas foram adicionadas a `Preferencias`, ao painel e à
      persistência, se forem alteráveis pelo usuário.

Antes de concluir:

- [ ] `python -m compileall -q app.py ocr_captura` passa sem erros.
- [ ] `python app.py` inicia e mostra os motores/atalhos corretamente.
- [ ] Fiz um teste manual de captura quando a mudança afeta o fluxo.
- [ ] Testei `Alt+P`, os três interruptores e a persistência, se aplicável.
- [ ] README foi atualizado para comportamento/configuração nova.
- [ ] `GUIA_PYTHON.md` foi atualizado se o padrão de código mudou.
- [ ] `ocr_captura/__init__.py` e a árvore do README incluem módulos novos.
- [ ] Se afetou o pacote, rodei `empacotamento/build.ps1 -SemInstalador` e
      testei o executável gerado.
- [ ] Se afetou o instalador, testei instalar, abrir e desinstalar.
- [ ] Se afetou o workflow, validei o YAML e a versão gerada em um build local.
- [ ] Não incluí arquivos gerados, resultados, segredos ou mudanças alheias.

### Validação

```powershell
python -m compileall -q app.py ocr_captura
python app.py
```

Teste manual mínimo, quando aplicável:

1. Pressione `Alt + P` e confirme que o painel abre e fecha.
2. Com o OCR ligado, pressione `Print Screen` ou `Win + Shift + S`.
3. Recorte um texto e confirme a mensagem `[OCR]` no console ou no log.
4. Confirme o arquivo em `resultados_historico/` no código-fonte ou em
   `%APPDATA%\OCR Capturas\resultados_historico\` no instalado, se o histórico
   estiver ligado.
5. Confirme o texto no clipboard, se "copiar texto" estiver ligado.
6. Desligue o OCR, recorte outro texto e confirme que a imagem continua no
   clipboard.
7. Feche e reabra o app e confirme que as escolhas do painel foram mantidas.

Testes automatizados são bem-vindos, especialmente para funções puras de
`imagens.py`. Quando existirem, coloque-os em `testes/` e rode com
`python -m pytest`. Não deixe a suíte quebrada.

---

## 6. Documentação

- **`README.md`**: comportamento para quem usa o app. Toda configuração nova,
  atalho novo ou mudança visível precisa aparecer aqui.
- **`GUIA_PYTHON.md`**: material didático. Se você introduzir um recurso de
  Python que ainda não está explicado, atualize o guia e use exemplos do
  código real.
- **`AGENTS.md`**: regras de arquitetura e processo. Atualize quando a
  estrutura de módulos mudar.
- **Docstrings**: explique o "por quê" e os detalhes não óbvios, não apenas
  repita o nome da função.

---

## 7. Git: commit somente com permissão explícita

**Regra obrigatória:** nunca crie, altere ou publique commits sem autorização
explícita do usuário.

Por padrão, **não execute**:

- `git add` ou `git commit` (incluindo `--amend`);
- `git push`, `git tag` ou `gh pr create`;
- `git reset --hard`, `git rebase`, `git merge` ou qualquer reescrita de
  histórico;
- force push, bypass de hooks ou alteração de configuração do Git.

Comandos somente leitura são permitidos para entender o estado do repositório:
`git status`, `git diff`, `git log`, `git show`, `git branch --list`.

Regras de autorização:

1. Um pedido como "implemente esta feature" autoriza apenas a alteração dos
   arquivos, **não** o commit.
2. "Pode commitar" autoriza um commit do trabalho atual, não push nem PR.
3. "Pode commitar e enviar" autoriza commit e push; PR ainda exige pedido
   explícito.
4. A permissão vale para a tarefa/conversa atual. Não a trate como permissão
   permanente para mudanças futuras.
5. Antes de commitar, mostre `git status` e `git diff`, confirme que só há
   mudanças intencionais e não inclua arquivos alheios ou não rastreados.
6. Nunca faça commit com testes quebrados ou com segredos/resultados gerados.
7. Se houver dúvida sobre o que incluir, pergunte antes de commitar.

Ao finalizar uma tarefa sem autorização de commit, deixe as alterações no
working tree e informe o que mudou e como validar.

---

## 8. Empacotamento e distribuição

O produto para outros usuários é gerado por `empacotamento/build.ps1`:

1. valida o Tesseract instalado na máquina de build e os idiomas de
   `IDIOMAS_TESSERACT`, acrescentando `osd`;
2. copia `tesseract.exe`, as DLLs e os `.traineddata` para
   `build/tesseract` (pasta ignorada pelo Git);
3. roda o PyInstaller com `empacotamento/ocr_capturas.spec`, em modo
   `--onedir` e `--windowed`;
4. cria `dist/OCR-Capturas-<versao>-portable.zip`;
5. compila `dist/instalador/OCR-Capturas-<versao>-instalador.exe` com Inno Setup.

Comandos úteis:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\empacotamento\build.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\empacotamento\build.ps1 -SemInstalador
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\empacotamento\build.ps1 -PularInstalacao
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\empacotamento\build.ps1 -Versao 1.0.1
```

Regras de empacotamento:

- O executável usa `caminhos.py` para achar `_internal/tesseract` e para
  gravar dados em `%APPDATA%`/`%LOCALAPPDATA%`. Não grave nada em `_internal`
  nem na pasta de instalação.
- `TESSDATA_PREFIX` deve apontar para a própria pasta `tessdata`; apontar para
  o pai faz `--list-langs` devolver `tessdata/eng` em vez de `eng`.
- O log fica em `%LOCALAPPDATA%\OCR Capturas\ocr.log`; o executável é
  `--windowed` e redireciona `print`/`stderr` para lá.
- `--painel` abre o painel ao iniciar. O atalho do menu Iniciar usa
  `--painel`; o início automático com o Windows usa o modo silencioso.
- O mutex de `instancia.py` precisa ter o mesmo nome de `AppMutex` em
  `empacotamento/instalador.iss`.
- O instalador é `.exe` do Inno Setup, por usuário, sem admin. MSI não faz
  parte deste fluxo.
- Tesseract é Apache 2.0; mantenha `_internal\tesseract\LICENSE` no pacote.
- `build/` e `dist/` não são versionados. Não inclua executáveis, ZIPs,
  resultados de teste, `.venv` ou segredos no commit.
- A versão local padrão é `1.0.0`; use `-Versao X.Y.Z` para outra. O
  `empacotamento/version_info.txt` é um template com placeholders; o build
  gera `build/version_info.txt` e passa a mesma versão ao Inno Setup por
  `/DMyAppVersion`. Não edite a versão em vários arquivos manualmente.
- `.github/workflows/release.yml` roda em cada push para `main` (e por
  `workflow_dispatch`). A versão automática é `1.0.<run_number>`, a tag é
  `v<versao>` e os assets são o instalador, o ZIP portátil e
  `SHA256SUMS.txt`. O workflow precisa de `contents: write`, já declarado.
- O runner instala Tesseract e Inno Setup e baixa os modelos de
  `IDIOMAS_TESSERACT` de `tessdata_best`; não dependa de ferramentas
  preinstaladas na máquina do usuário para o release.
- Se uma release da tag já existir, o workflow substitui os assets com
  `gh release upload --clobber`; não crie tags manualmente com o mesmo nome.

Validação de distribuição:

```powershell
# Gera o executável, o ZIP e o instalador na versão 1.0.1
.\empacotamento\build.ps1 -Versao 1.0.1
dist\OCR-Capturas\OCR-Capturas.exe --painel

# Instala silenciosamente para testar o instalador
dist\instalador\OCR-Capturas-1.0.1-instalador.exe /VERYSILENT /SUPPRESSMSGBOXES
# Depois desinstale pelo atalho ou por Configurações > Aplicativos.
```

---

## 9. Resumo para o agente

1. Leia README, GUIA e os arquivos envolvidos.
2. Escolha o módulo pela responsabilidade, não pela conveniência.
3. Preserve os contratos e a direção das dependências.
4. Mantenha nomes, type hints, docstrings e mensagens no padrão do projeto.
5. Valide com `compileall` e, quando possível, com um teste manual.
6. Se mexeu no pacote, valide o executável e/ou o instalador.
7. Atualize a documentação junto com o código.
8. **Não faça commit, push ou PR sem permissão explícita.**
