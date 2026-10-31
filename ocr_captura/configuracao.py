"""Configurações do aplicativo.

Este é o arquivo que você deve editar para ajustar o comportamento do OCR.
Em Python, nomes em MAIÚSCULAS são uma convenção para constantes: valores que
não devem ser alterados enquanto o programa está rodando.
"""

# Idiomas do OCR do Windows, em ordem de preferência. O primeiro que estiver
# instalado será usado como alternativa ao Tesseract. O app mostra o idioma
# escolhido na inicialização.
IDIOMAS_OCR: tuple[str, ...] = ("pt-BR", "pt-PT", "en-US")

# O Tesseract é o motor principal. Se ele não devolver nenhum texto, o app
# usa o OCR nativo do Windows como alternativa. O Tesseract precisa do
# executável Tesseract-OCR instalado (o pytesseract sozinho não basta).
# Coloque False para usar apenas o OCR do Windows.
USAR_TESSERACT = True

# Idiomas do Tesseract, no formato que ele aceita. "por+eng" usa português e
# inglês juntos. Os arquivos .traineddata de cada idioma precisam estar
# instalados (veja `tesseract --list-langs`).
IDIOMAS_TESSERACT = "por+eng"

# Caminho do executável do Tesseract. Deixe vazio para o app procurar no PATH
# e na pasta padrão de instalação (C:\Program Files\Tesseract-OCR).
CAMINHO_TESSERACT = ""

# Tempo máximo, em segundos, para o usuário concluir o recorte.
ESPERA_CAPTURA_SEGUNDOS = 30.0

# Intervalo entre as verificações da área de transferência.
# 0.08 s = 80 ms. Valores menores que isso gastam CPU sem melhorar a resposta.
INTERVALO_VERIFICACAO_SEGUNDOS = 0.08

# Se True, copia o texto reconhecido para a área de transferência.
# Atenção: isso substitui a imagem capturada.
COPIAR_RESULTADO = True

# Os motores de OCR acertam mais em imagens maiores. Capturas cujo maior lado
# seja menor que LADO_ALVO_OCR são ampliadas, respeitando ESCALA_MAXIMA.
LADO_ALVO_OCR = 2500
ESCALA_MAXIMA = 2.0

# Só vale a pena ampliar se o ganho for de pelo menos 20%.
FATOR_MINIMO_DE_AMPLIACAO = 1.2

# Extração de texto claro sobreposto (títulos de vídeo, legendas, etc.).
# O app procura pixels claros e com baixa saturação (branco/cinza), separa
# as linhas e tenta o Tesseract em cada uma. A faixa de cobertura evita
# aplicar a extração em capturas comuns (fundo branco ou escuro).
TEXTO_CLARO_SATURACAO_MAXIMA = 0.14  # 0 = cinza; 1 = cor saturada
TEXTO_CLARO_BRILHO_MINIMO = 0.50     # 0 = preto; 1 = branco
TEXTO_CLARO_COBERTURA_MINIMA = 0.02  # 2% dos pixels da imagem
TEXTO_CLARO_COBERTURA_MAXIMA = 0.40  # 40% dos pixels da imagem

# A área de transferência pode ficar bloqueada por alguns milissegundos
# enquanto outro programa escreve nela. As operações tentam de novo
# TENTATIVAS_CLIPBOARD vezes, esperando INTERVALO_TENTATIVA_SEGUNDOS.
TENTATIVAS_CLIPBOARD = 5
INTERVALO_TENTATIVA_SEGUNDOS = 0.1

# Se True, salva o texto reconhecido em um arquivo .txt.
SALVAR_RESULTADO = True

# Pasta onde os arquivos serão salvos. O caminho é relativo à pasta de onde
# você executa `python app.py`. A pasta é criada automaticamente
PASTA_RESULTADOS = "resultados_historico"