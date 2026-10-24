# OCR de capturas de tela (Windows)

Pressione **Print Screen** ou **Win + Shift + S** (ou **Ctrl + Win + S**) e o
app reconhece o texto da imagem que estiver na área de transferência.

O texto reconhecido é exibido no console e copiado para a área de
transferência (substituindo a imagem capturada).

## Requisitos

- Windows 10 ou 11
- Python 3.10+ (testado com Python 3.13)
- Um idioma com OCR instalado no Windows

O app usa o **OCR nativo do Windows** (`Windows.Media.Ocr`). Não é preciso
instalar Tesseract nem baixar modelos.

Para conferir/instalar o idioma de OCR:

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
    imagens.py                  conversão para RGB e ampliação para o OCR
    area_transferencia.py       leitura/escrita do clipboard do Windows
    ocr.py                      integração com o OCR nativo (WinRT)
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
5. `MotorOcr.reconhecer()` prepara a imagem e chama o OCR do Windows.
6. O texto é exibido e, se `COPIAR_RESULTADO` estiver ligado, copiado para o
   clipboard.

## Configurações

No arquivo `ocr_captura/configuracao.py`:

- `COPIAR_RESULTADO`: se `True`, copia o texto reconhecido para a área de
  transferência (e substitui a imagem). Coloque `False` para manter a imagem.
- `ESPERA_CAPTURA_SEGUNDOS`: tempo máximo, em segundos, para concluir o recorte.
- `IDIOMAS_OCR`: ordem de preferência dos idiomas de OCR.
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
- **Nenhum texto é reconhecido**: confira se o idioma com OCR está instalado
  (veja acima). O app lista o idioma usado na inicialização.
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
