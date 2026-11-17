# OCR de capturas de tela (Windows)

Pressione **Print Screen** ou **Win + Shift + S** (ou **Ctrl + Win + S**) e o
app reconhece o texto da imagem que estiver na área de transferência.

O texto reconhecido é exibido no terminal (no código-fonte) ou no arquivo de
log (no aplicativo instalado) e publicado conforme as opções do painel
lateral: pode substituir a imagem no clipboard, ser salvo em `.txt` ou apenas
ser exibido no diagnóstico.

**Alt + P** abre um painel lateral para ligar/desligar o OCR na hora. Com o
OCR desligado, nenhum reconhecimento é executado e a captura continua sendo
apenas uma imagem na área de transferência, pronta para colar.

## Requisitos

### Para usar o instalador ou o pacote portátil

- Windows 10 ou 11, 64 bits.
- Nenhuma instalação de Python ou Tesseract é necessária: o pacote inclui o
  Tesseract e os idiomas `por+eng`.
- Opcional: um idioma com OCR instalado no Windows (motor alternativo).

### Para rodar a partir do código-fonte

- Python 3.10+ (testado com Python 3.13).
- Tesseract-OCR instalado (motor principal).
- Opcional: um idioma com OCR instalado no Windows (motor alternativo).

A interface usa `tkinter`, que acompanha o Python oficial do Windows.

O app usa o **Tesseract** como motor principal. Se ele não devolver nenhum
texto, o app tenta o **OCR nativo do Windows** (`Windows.Media.Ocr`) como
alternativa. O fallback do Windows é opcional: sem ele, o app continua
funcionando apenas com o Tesseract.

Para instalar o Tesseract no Windows, use o instalador oficial
(<https://github.com/UB-Mannheim/tesseract/wiki>) ou o winget:

```powershell
winget install --id UB-Mannheim.TesseractOCR
```

Marque os idiomas desejados no instalador (Português e Inglês). A instalação
silenciosa do winget inclui apenas o inglês; nesse caso, adicione o arquivo
`por.traineddata` à pasta `tessdata` da instalação (ou rode o instalador de
novo e selecione o português).

> O pacote `pytesseract` é apenas a ponte em Python. Ele não inclui o
> executável do Tesseract.

No modo instalado, o Tesseract portátil incluído tem prioridade. No
código-fonte, o app procura o executável no `PATH` e em
`C:\Program Files\Tesseract-OCR`; se estiver em outro lugar, ajuste
`CAMINHO_TESSERACT` em `ocr_captura/configuracao.py`. Idiomas configurados que
não estiverem instalados são ignorados com um aviso na inicialização.

Para habilitar o fallback do Windows, instale o OCR do idioma:

1. Abra **Configurações > Hora e idioma > Idioma e região**.
2. Selecione o idioma (ex.: Português (Brasil)) e clique em **Opções de idioma**.
3. Em **Recursos de idioma**, instale **OCR** (Reconhecimento óptico de caracteres).

O app tenta, nesta ordem: `pt-BR`, `pt-PT` e `en-US`. Depois, usa o idioma do
perfil do usuário.

## Instalação

### Usando o instalador

Baixe o arquivo mais recente na página **Releases** do repositório e execute
`OCR-Capturas-<versao>-instalador.exe`. A instalação é feita apenas para o
usuário atual, não pede senha de administrador e não instala o Tesseract no
sistema: ele vai junto com o aplicativo.

O instalador cria um atalho no menu Iniciar. Esse atalho abre o painel de
controle; o aplicativo continua rodando em segundo plano quando o painel é
fechado. Também é possível marcar a criação de um atalho na área de trabalho e
o início automático com o Windows.

O instalador e o executável não têm assinatura digital. Se o Windows mostrar
"O Windows protegeu o computador", clique em **Mais informações** e depois em
**Executar assim mesmo**. Para distribuir sem esse aviso, é necessário assinar
o executável com um certificado de code signing.

### Usando o pacote portátil

Baixe `OCR-Capturas-<versao>-portable.zip` na página **Releases**, extraia e
execute `OCR-Capturas\OCR-Capturas.exe`. O pacote portátil não cria atalhos;
use `Alt+P` para abrir o painel.

### Rodando a partir do código-fonte

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso

```powershell
python app.py
```

Para abrir o painel assim que o app iniciar:

```powershell
python app.py --painel
```

Atalhos:

| Atalho | Comportamento |
| --- | --- |
| `Alt + P` | Abre ou fecha o painel lateral de configuração. |
| `Print Screen` | Comportamento definido no Windows: abre a ferramenta de recorte (padrão do Windows 11) ou copia a tela inteira. |
| `Win + Shift + S` | Abre a ferramenta de recorte nativa. |
| `Ctrl + Win + S` | Dispara o atalho nativo `Win + Shift + S` (esse atalho não é nativo do Windows). |

Depois de selecionar a área e confirmar o recorte, aguarde a mensagem de OCR.
No código-fonte ela aparece no terminal; no aplicativo instalado, o texto é
copiado para o clipboard e/ou salvo, e o diagnóstico fica no arquivo de log.

> Rodando com `python app.py`, o terminal precisa continuar aberto para os
> atalhos e o OCR funcionarem. Se você fechar o terminal, o programa para.
> No aplicativo instalado não há terminal: ele fica em segundo plano e é
> encerrado pelo botão **Encerrar aplicativo** do painel (`Alt+P`).

## Gerando o executável e o instalador

O build é feito com **PyInstaller** (executável em pasta, `--onedir`) e
**Inno Setup** (instalador `.exe`). O Tesseract é copiado para dentro do
pacote; quem instala não precisa ter Python nem Tesseract.

Pré-requisitos de build:

- Windows 10/11 de 64 bits.
- Python 3.10+ com o ambiente virtual do projeto.
- Tesseract instalado na máquina de build, com os idiomas `por`, `eng` e
  `osd` (o script valida os arquivos antes de empacotar).
- Inno Setup 6:

  ```powershell
  winget install --id JRSoftware.InnoSetup
  ```

- Dependências de build no ambiente virtual:

  ```powershell
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements-dev.txt
  ```

Para gerar tudo:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\empacotamento\build.ps1
```

O `-ExecutionPolicy Bypass` vale só para essa execução. Se a política de
execução do seu Windows já permitir scripts locais,
`.\empacotamento\build.ps1` também funciona.

O script:

1. valida o Tesseract e os idiomas configurados em `IDIOMAS_TESSERACT`;
2. copia uma versão portátil do Tesseract para `build/tesseract`;
3. executa o PyInstaller com `empacotamento/ocr_capturas.spec`;
4. cria o ZIP portátil;
5. compila o instalador com Inno Setup.

Saídas em `dist/` (a versão padrão é `1.0.0`):

```text
dist\OCR-Capturas\OCR-Capturas.exe                  pasta portátil
dist\OCR-Capturas-1.0.0-portable.zip                pacote portátil
dist\instalador\OCR-Capturas-1.0.0-instalador.exe   instalador
```

Opções úteis:

- `-SemInstalador`: gera só a pasta portátil e o ZIP, sem Inno Setup.
- `-PularInstalacao`: não executa `pip install` antes do build.
- `-Versao 1.0.1`: gera os arquivos com outra versão.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\empacotamento\build.ps1 -Versao 1.0.1
```

O instalador gerado é um `.exe` do Inno Setup, não um `.msi`. Para uma
distribuição corporativa que exija MSI, seria necessário um projeto WiX ou
uma ferramenta como o Advanced Installer; o fluxo atual prioriza o instalador
`.exe`, que é mais simples para um utilitário de usuário.

O ícone é gerado por `empacotamento/gerar_icone.py`. O arquivo
`empacotamento/version_info.txt` é um template: o build preenche os
placeholders em `build/version_info.txt`, e o Inno Setup recebe a mesma versão
por `/DMyAppVersion`. Não é preciso editar a versão em vários arquivos.

O Tesseract é distribuído sob a licença Apache 2.0. A licença é copiada para
`_internal\tesseract\LICENSE` dentro do executável. O instalador e o
executável não são assinados digitalmente; para evitar o aviso do SmartScreen,
é preciso um certificado de code signing.

## Releases automáticos no GitHub

O workflow [`.github/workflows/release.yml`](.github/workflows/release.yml)
gera e publica uma release sempre que um commit chega à branch `main`. Ele
também pode ser iniciado manualmente pela aba **Actions** do GitHub
(**Build e release > Run workflow**, escolhendo a branch `main`).

A versão automática é:

```text
1.0.<número da execução do workflow>
```

Por exemplo, a execução 42 publica a tag `v1.0.42`. O número sempre aumenta,
então cada release tem uma versão própria. Para mudar a base `1.0`, edite
`VERSAO_BASE` no início do workflow.

Cada release recebe estes assets:

```text
OCR-Capturas-<versao>-instalador.exe
OCR-Capturas-<versao>-portable.zip
SHA256SUMS.txt
```

O workflow roda em `windows-latest`, instala Python, Tesseract e Inno Setup,
baixa os modelos de idioma configurados em `IDIOMAS_TESSERACT` e executa
`build.ps1 -Versao <versao>`. Ele precisa de permissão de escrita em
**Contents**; o próprio workflow declara `contents: write` no token do GitHub
Actions.

Se a release daquela tag já existir, o workflow substitui os assets em vez de
falhar. Isso permite reexecutar uma execução sem criar uma release duplicada.

## Painel lateral (Alt + P)

O painel abre pela direita, fica sobre as outras janelas e fecha com `Alt + P`
ou `Esc`. Ele tem três opções:

- **Reconhecer texto (OCR)**: desligado, nenhum OCR é executado. A captura
  continua sendo uma imagem na área de transferência, pronta para colar em
  outro programa.
- **Copiar texto reconhecido**: ligado, o texto substitui a imagem no
  clipboard. Desligado, a imagem continua disponível.
- **Salvar histórico em .txt**: grava o texto reconhecido na pasta de
  resultados do usuário (veja **Onde ficam os dados** abaixo).

As opções de resultado ficam desabilitadas quando o OCR está desligado. As
alterações valem imediatamente e são salvas em:

```text
%APPDATA%\OCR Capturas\preferencias.json
```

O arquivo é criado na primeira alteração feita no painel. As constantes de
`configuracao.py` são usadas como valores padrão; se o arquivo existir, ele
tem prioridade. Para voltar aos padrões, feche o app e apague esse arquivo.

O painel também tem o botão **Encerrar aplicativo**, que fecha o app de forma
limpa. No código-fonte ele equivale a `Ctrl+C` no terminal.

## Onde ficam os dados

No aplicativo instalado, os arquivos do usuário ficam fora da pasta de
instalação:

```text
%APPDATA%\OCR Capturas\preferencias.json
%APPDATA%\OCR Capturas\resultados_historico\
%LOCALAPPDATA%\OCR Capturas\ocr.log
```

O log é usado principalmente porque o executável é uma aplicação de janela,
sem console. Ele ajuda a diagnosticar se o Tesseract e o OCR do Windows foram
carregados e mostra o texto reconhecido.

No código-fonte, o histórico continua sendo gravado em
`resultados_historico/`, relativo à pasta de onde você executa `python app.py`.
As preferências continuam em `%APPDATA%\OCR Capturas\preferencias.json`.
Desinstalar o aplicativo não apaga preferências nem resultados.

## Como o código está organizado

O `app.py` é apenas o ponto de entrada. A implementação fica no pacote
`ocr_captura/`, dividida por responsabilidade:

```text
app.py                          ponto de entrada; cria as peças e inicia o app
ocr_captura/
    configuracao.py             valores padrão que você pode ajustar
    caminhos.py                 recursos do executável e pastas do usuário
    preferencias.py             opções do painel, salvas em JSON
    painel.py                   painel lateral Tkinter (Alt+P)
    imagens.py                  conversão, ampliação e texto claro sobreposto
    area_transferencia.py       leitura/escrita do clipboard do Windows
    ocr.py                      Tesseract (principal) e OCR do Windows (fallback)
    atalhos.py                  atalhos globais de teclado
    captura.py                  laço principal e estado da captura
    instancia.py                evita duas cópias do app ao mesmo tempo
empacotamento/                  PyInstaller, Inno Setup e script de build
.github/workflows/release.yml   build e release automáticos no GitHub
requirements-dev.txt            dependências para gerar o executável
GUIA_PYTHON.md                  conceitos de Python usados no projeto
```

O fluxo de uma captura:

1. `Atalhos` registra **Print Screen**, **Win+Shift+S**, **Ctrl+Win+S** e
   **Alt+P**.
2. Quando um atalho de captura é pressionado, `MonitorCapturas.armar()`
   verifica se o OCR está ligado. Se estiver desligado, a imagem continua no
   clipboard e o fluxo termina.
3. Com o OCR ligado, `armar()` guarda a sequência atual do clipboard e um
   prazo para a imagem chegar.
4. O laço do monitor compara a sequência do clipboard a cada 80 ms.
5. Quando a sequência muda e existe uma captura armada,
   `AreaTransferencia.ler_imagem()` lê a imagem.
6. `MotorOcr.reconhecer()` chama o Tesseract na imagem preparada.
7. Ele também tenta extrair texto claro sobreposto (títulos e legendas) e
   fica com o resultado mais completo.
8. Se o Tesseract não devolver texto, `MotorOcr` tenta o OCR do Windows.
9. O texto é exibido e, conforme as preferências, copiado para o clipboard
   e/ou salvo na pasta de resultados.

O painel roda na thread principal (é ela que executa o `mainloop` do Tkinter);
o monitor de capturas roda em uma thread `daemon`. O callback do `Alt+P` só
coloca um pedido em uma fila, consumida pelo painel na thread principal.

## Configurações

No arquivo `ocr_captura/configuracao.py`:

- `OCR_ATIVO`: se `True` (padrão), o OCR começa ligado. O painel lateral pode
  alternar em tempo de execução.
- `COPIAR_RESULTADO`: valor padrão de "copiar texto". Se `True`, o texto
  reconhecido substitui a imagem no clipboard. O painel lateral pode alterar
  em tempo de execução.
- `SALVAR_RESULTADO`: valor padrão de "salvar histórico". Se `True`, grava o
  texto reconhecido em um `.txt` na pasta de resultados. O painel lateral pode
  alterar em tempo de execução.
- `ESPERA_CAPTURA_SEGUNDOS`: tempo máximo, em segundos, para concluir o recorte.
- `IDIOMAS_OCR`: ordem de preferência dos idiomas de OCR do Windows.
- `USAR_TESSERACT`: se `True` (padrão), usa o Tesseract como motor principal;
  se `False`, usa apenas o OCR do Windows.
- `IDIOMAS_TESSERACT`: idiomas usados pelo Tesseract (ex.: `"por+eng"`). No
  código-fonte, eles precisam estar instalados; no build, são copiados para o
  pacote. Para usar outros idiomas no aplicativo instalado, edite esta opção,
  instale os idiomas na máquina de build e gere o executável novamente.
- `CAMINHO_TESSERACT`: caminho do `tesseract.exe`; vazio faz o app procurar
  no `PATH` e na pasta padrão. No executável, o Tesseract embutido tem
  prioridade.
- `PASTA_RESULTADOS`: nome da pasta de resultados. No código-fonte ela é
  relativa à pasta de onde você executa `python app.py`; no executável fica
  em `%APPDATA%\OCR Capturas\resultados_historico`.
- `PASTA_PREFERENCIAS`, `ARQUIVO_PREFERENCIAS`: pasta e nome do JSON de
  preferências, dentro de `%APPDATA%`.
- `TEXTO_CLARO_SATURACAO_MAXIMA`, `TEXTO_CLARO_BRILHO_MINIMO`: controlam a
  máscara de texto claro/neutro sobreposto à imagem.
- `TEXTO_CLARO_COBERTURA_MINIMA`, `TEXTO_CLARO_COBERTURA_MAXIMA`: faixa de
  cobertura em que a máscara é aplicada; evita processar capturas comuns com
  fundo branco ou escuro.
- `LADO_ALVO_OCR`, `ESCALA_MAXIMA` e `FATOR_MINIMO_DE_AMPLIACAO`: controlam a
  ampliação de capturas pequenas.
- `TENTATIVAS_CLIPBOARD`, `INTERVALO_TENTATIVA_SEGUNDOS`: novas tentativas
  quando o Windows mantém o clipboard bloqueado por alguns milissegundos.

As opções alteradas no painel são gravadas em
`%APPDATA%\OCR Capturas\preferencias.json` e têm prioridade sobre as
constantes acima. Para voltar aos padrões, apague esse arquivo com o app
fechado. No aplicativo instalado, não é possível editar
`configuracao.py`; as opções ajustáveis continuam disponíveis no painel.

## Entendendo o código

Se você programa em outra linguagem e está aprendendo Python, comece pelo
[`GUIA_PYTHON.md`](GUIA_PYTHON.md). Ele explica, com exemplos deste projeto:

- módulos, pacotes e imports;
- funções, classes, `self` e type hints;
- `@dataclass`, `@staticmethod` e imutabilidade;
- `with`, `try/except/finally` e locks;
- threads, callbacks, filas e por que o estado da captura tem um `Lock`;
- Tkinter, `mainloop` e por que os widgets ficam na thread principal;
- `async`/`await`, `asyncio.run` e a ponte com o WinRT;
- list/dict comprehensions e generator expressions;
- o caminho completo de uma captura, arquivo por arquivo.

## Problemas comuns

- **Instalei, mas não vejo janela**: o app roda em segundo plano. Clique no
  atalho **OCR de Capturas** do menu Iniciar, que abre o painel, ou pressione
  `Alt+P`. O diagnóstico fica em
  `%LOCALAPPDATA%\OCR Capturas\ocr.log`.
- **O Windows bloqueou o instalador**: ele não tem assinatura digital. Clique
  em **Mais informações** e depois em **Executar assim mesmo**. Para eliminar
  o aviso, assine o executável e o instalador com um certificado de code
  signing.
- **Onde estão os resultados e o log**: no aplicativo instalado, o histórico
  fica em `%APPDATA%\OCR Capturas\resultados_historico\` e o log em
  `%LOCALAPPDATA%\OCR Capturas\ocr.log`. Veja **Onde ficam os dados**.
- **Abri o app duas vezes**: a segunda cópia mostra um aviso e encerra. Use
  `Alt+P` para abrir o painel da cópia que já está rodando.
- **Como desinstalar**: use **Configurações > Aplicativos > Aplicativos
  instalados > OCR de Capturas > Desinstalar**, ou o atalho de desinstalação
  do menu Iniciar. Preferências e resultados não são apagados.
- **Os atalhos não funcionam**: no código-fonte, execute o terminal como
  administrador, principalmente se o app em foco também estiver elevado. No
  aplicativo instalado, execute o atalho como administrador se precisar capturar
  janelas elevadas. Alguns jogos que usam entrada direta (raw input) podem não
  ser capturados.
- **Alt + P não abre o painel**: verifique se outro programa usa o mesmo
  atalho global. Alguns aplicativos elevados também podem impedir o hook de
  teclado de receber a combinação; nesse caso, execute o app como administrador.
- **Print Screen não copia nada**: no Windows 11, por padrão, ele abre a
  ferramenta de recorte. Se a opção estiver desativada, verifique se o Windows
  está configurado para copiar a tela para a área de transferência.
- **Nenhum texto é reconhecido**: veja a mensagem de inicialização (no
  terminal ou em `%LOCALAPPDATA%\OCR Capturas\ocr.log`) para saber qual motor
  foi carregado. Confirme os idiomas do Tesseract com
  `tesseract --list-langs` e, se o fallback do Windows for usado, se o OCR do
  idioma está instalado.
- **O Tesseract não é usado**: a mensagem de inicialização avisa quando o
  `pytesseract` ou o executável do Tesseract não foram encontrados. No
  aplicativo instalado, o Tesseract vai em
  `_internal\tesseract\tesseract.exe`; se ele estiver ausente, reinstale o
  aplicativo. No código-fonte, rode
  `& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs` (ou
  `tesseract --list-langs`, se ele estiver no `PATH`) para ver os idiomas
  instalados e confirme se eles batem com `IDIOMAS_TESSERACT`. Se o
  executável estiver fora do `PATH`, defina `CAMINHO_TESSERACT`.
- **O fallback do Windows não é usado**: instale o recurso de OCR do idioma
  nas configurações do Windows (veja acima). O app continua funcionando
  apenas com o Tesseract.
- **`Ctrl + Win + S`**: como não é um atalho nativo, o app dispara
  `Win + Shift + S` por software. Se preferir o atalho nativo, use
  `Win + Shift + S` diretamente.
- **A tela de recorte não abre**: às vezes o Windows acumula processos
  travados do Snipping Tool. Feche-os e tente de novo:

  ```powershell
  Get-Process SnippingTool -ErrorAction SilentlyContinue | Stop-Process -Force
  ```

  Se continuar, repare o aplicativo em **Configurações > Aplicativos >
  Aplicativos instalados > Snipping Tool > Opções avançadas > Reparar**
  (ou **Redefinir**).
