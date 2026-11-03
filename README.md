# OCR de capturas de tela (Windows)

Pressione **Print Screen** ou **Win + Shift + S** (ou **Ctrl + Win + S**) e o
app reconhece o texto da imagem que estiver na área de transferência.

O texto reconhecido é exibido no console e publicado conforme as opções do
painel lateral: pode substituir a imagem no clipboard, ser salvo em `.txt` ou
apenas aparecer no console.

**Alt + P** abre um painel lateral para ligar/desligar o OCR na hora. Com o
OCR desligado, nenhum reconhecimento é executado e a captura continua sendo
apenas uma imagem na área de transferência, pronta para colar.

## Requisitos

- Windows 10 ou 11
- Python 3.10+ (testado com Python 3.13)
- Tesseract-OCR instalado (motor principal)
- Opcional: um idioma com OCR instalado no Windows (motor alternativo)

A interface usa `tkinter`, que acompanha o Python oficial do Windows. Não há
dependência nova.

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

O app procura o executável no `PATH` e em `C:\Program Files\Tesseract-OCR`;
se estiver em outro lugar, ajuste `CAMINHO_TESSERACT` em
`ocr_captura/configuracao.py`. Idiomas configurados que não estiverem
instalados são ignorados com um aviso na inicialização.

Para habilitar o fallback do Windows, instale o OCR do idioma:

1. Abra **Configurações > Hora e idioma > Idioma e região**.
2. Selecione o idioma (ex.: Português (Brasil)) e clique em **Opções de idioma**.
3. Em **Recursos de idioma**, instale **OCR** (Reconhecimento óptico de caracteres).

O app tenta, nesta ordem: `pt-BR`, `pt-PT` e `en-US`. Depois, usa o idioma do
perfil do usuário.

## Instalação

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso

```powershell
python app.py
```

Atalhos:

| Atalho | Comportamento |
| --- | --- |
| `Alt + P` | Abre ou fecha o painel lateral de configuração. |
| `Print Screen` | Comportamento definido no Windows: abre a ferramenta de recorte (padrão do Windows 11) ou copia a tela inteira. |
| `Win + Shift + S` | Abre a ferramenta de recorte nativa. |
| `Ctrl + Win + S` | Dispara o atalho nativo `Win + Shift + S` (esse atalho não é nativo do Windows). |

Depois de selecionar a área e confirmar o recorte, aguarde a mensagem de OCR
no console.

> O `app.py` precisa continuar rodando no terminal para os atalhos e o OCR
> funcionarem. Se você fechar o terminal, o programa para. O `Win + Shift + S`
> e o `Print Screen` continuam abrindo o recorte do Windows normalmente, mas
> sem o OCR.

## Painel lateral (Alt + P)

O painel abre pela direita, fica sobre as outras janelas e fecha com `Alt + P`
ou `Esc`. Ele tem três opções:

- **Reconhecer texto (OCR)**: desligado, nenhum OCR é executado. A captura
  continua sendo uma imagem na área de transferência, pronta para colar em
  outro programa.
- **Copiar texto reconhecido**: ligado, o texto substitui a imagem no
  clipboard. Desligado, a imagem continua disponível.
- **Salvar histórico em .txt**: grava o texto reconhecido na pasta
  `resultados_historico/`.

As opções de resultado ficam desabilitadas quando o OCR está desligado. As
alterações valem imediatamente e são salvas em:

```text
%APPDATA%\OCR Capturas\preferencias.json
```

O arquivo é criado na primeira alteração feita no painel. As constantes de
`configuracao.py` são usadas como valores padrão; se o arquivo existir, ele
tem prioridade. Para voltar aos padrões, feche o app e apague esse arquivo.

O painel também tem o botão **Encerrar aplicativo**, que fecha o app de forma
limpa (equivalente a `Ctrl+C` no terminal).

## Como o código está organizado

O `app.py` é apenas o ponto de entrada. A implementação fica no pacote
`ocr_captura/`, dividida por responsabilidade:

```text
app.py                          ponto de entrada; cria as peças e inicia o app
ocr_captura/
    configuracao.py             valores padrão que você pode ajustar
    preferencias.py             opções do painel, salvas em JSON
    painel.py                   painel lateral Tkinter (Alt+P)
    imagens.py                  conversão, ampliação e texto claro sobreposto
    area_transferencia.py       leitura/escrita do clipboard do Windows
    ocr.py                      Tesseract (principal) e OCR do Windows (fallback)
    atalhos.py                  atalhos globais de teclado
    captura.py                  laço principal e estado da captura
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
   e/ou salvo em `resultados_historico/`.

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
  texto reconhecido em um `.txt`. O painel lateral pode alterar em tempo de
  execução.
- `ESPERA_CAPTURA_SEGUNDOS`: tempo máximo, em segundos, para concluir o recorte.
- `IDIOMAS_OCR`: ordem de preferência dos idiomas de OCR do Windows.
- `USAR_TESSERACT`: se `True` (padrão), usa o Tesseract como motor principal;
  se `False`, usa apenas o OCR do Windows.
- `IDIOMAS_TESSERACT`: idiomas usados pelo Tesseract (ex.: `"por+eng"`).
- `CAMINHO_TESSERACT`: caminho do `tesseract.exe`; vazio faz o app procurar
  no `PATH` e na pasta padrão.
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
fechado.

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

- **Os atalhos não funcionam**: execute o terminal como administrador,
  principalmente se o app em foco também estiver elevado. Alguns jogos que usam
  entrada direta (raw input) podem não ser capturados.
- **Alt + P não abre o painel**: verifique se outro programa usa o mesmo
  atalho global. Alguns aplicativos elevados também podem impedir o hook de
  teclado de receber a combinação; nesse caso, execute o terminal como
  administrador.
- **Print Screen não copia nada**: no Windows 11, por padrão, ele abre a
  ferramenta de recorte. Se a opção estiver desativada, verifique se o Windows
  está configurado para copiar a tela para a área de transferência.
- **Nenhum texto é reconhecido**: veja a mensagem de inicialização para saber
  qual motor foi carregado. Confirme os idiomas do Tesseract com
  `tesseract --list-langs` e, se o fallback do Windows for usado, se o OCR do
  idioma está instalado.
- **O Tesseract não é usado**: a mensagem de inicialização avisa quando o
  `pytesseract` ou o executável do Tesseract não foram encontrados. Rode
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
