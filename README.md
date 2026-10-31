# OCR de capturas de tela (Windows)

Pressione **Print Screen** ou **Win + Shift + S** (ou **Ctrl + Win + S**) e o
app reconhece o texto da imagem que estiver na área de transferência.

O texto reconhecido é exibido no console e copiado para a área de
transferência (substituindo a imagem capturada).

## Requisitos

- Windows 10 ou 11
- Python 3.10+ (testado com Python 3.13)
- Tesseract-OCR instalado (motor principal)
- Opcional: um idioma com OCR instalado no Windows (motor alternativo)

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
| `Print Screen` | Comportamento definido no Windows: abre a ferramenta de recorte (padrão do Windows 11) ou copia a tela inteira. |
| `Win + Shift + S` | Abre a ferramenta de recorte nativa. |
| `Ctrl + Win + S` | Dispara o atalho nativo `Win + Shift + S` (esse atalho não é nativo do Windows). |

Depois de selecionar a área e confirmar o recorte, aguarde a mensagem de OCR
no console.

> O `app.py` precisa continuar rodando no terminal para os atalhos e o OCR
> funcionarem. Se você fechar o terminal, o programa para. O `Win + Shift + S`
> e o `Print Screen` continuam abrindo o recorte do Windows normalmente, mas
> sem o OCR.

## Como o código está organizado

O `app.py` é apenas o ponto de entrada. A implementação fica no pacote
`ocr_captura/`, dividida por responsabilidade:

```text
app.py                          ponto de entrada; cria as peças e inicia o app
ocr_captura/
    configuracao.py             valores que você pode ajustar
    imagens.py                  conversão, ampliação e texto claro sobreposto
    area_transferencia.py       leitura/escrita do clipboard do Windows
    ocr.py                      Tesseract (principal) e OCR do Windows (fallback)
    atalhos.py                  atalhos globais de teclado
    captura.py                  laço principal e estado da captura
GUIA_PYTHON.md                  conceitos de Python usados no projeto
```

O fluxo de uma captura:

1. `Atalhos` registra **Print Screen**, **Win+Shift+S** e **Ctrl+Win+S**.
2. Quando um atalho é pressionado, `MonitorCapturas.armar()` guarda a
   sequência atual do clipboard e um prazo para a imagem chegar.
3. O laço principal compara a sequência do clipboard a cada 80 ms.
4. Quando a sequência muda e existe uma captura armada,
   `AreaTransferencia.ler_imagem()` lê a imagem.
5. `MotorOcr.reconhecer()` chama o Tesseract na imagem preparada.
6. Ele também tenta extrair texto claro sobreposto (títulos e legendas) e
   fica com o resultado mais completo.
7. Se o Tesseract não devolver texto, `MotorOcr` tenta o OCR do Windows.
8. O texto é exibido e, se `COPIAR_RESULTADO` estiver ligado, copiado para o
   clipboard.

## Configurações

No arquivo `ocr_captura/configuracao.py`:

- `COPIAR_RESULTADO`: se `True`, copia o texto reconhecido para a área de
  transferência (e substitui a imagem). Coloque `False` para manter a imagem.
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

## Entendendo o código

Se você programa em outra linguagem e está aprendendo Python, comece pelo
[`GUIA_PYTHON.md`](GUIA_PYTHON.md). Ele explica, com exemplos deste projeto:

- módulos, pacotes e imports;
- funções, classes, `self` e type hints;
- `@dataclass`, `@staticmethod` e imutabilidade;
- `with`, `try/except/finally` e locks;
- threads, callbacks e por que o estado da captura tem um `Lock`;
- `async`/`await`, `asyncio.run` e a ponte com o WinRT;
- list/dict comprehensions e generator expressions;
- o caminho completo de uma captura, arquivo por arquivo.

## Problemas comuns

- **Os atalhos não funcionam**: execute o terminal como administrador,
  principalmente se o app em foco também estiver elevado. Alguns jogos que usam
  entrada direta (raw input) podem não ser capturados.
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
