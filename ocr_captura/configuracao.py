"""Configurações do aplicativo.

Este é o arquivo que você deve editar para ajustar o comportamento do OCR.
Em Python, nomes em MAIÚSCULAS são uma convenção para constantes: valores que
não devem ser alterados enquanto o programa está rodando.
"""

# Idiomas de OCR em ordem de preferência. O primeiro que estiver instalado no
# Windows será usado. Para ver os disponíveis, rode o app e leia a mensagem
# "[OCR] Idioma: ...".
IDIOMAS_OCR: tuple[str, ...] = ("pt-BR", "pt-PT", "en-US")

# Tempo máximo, em segundos, para o usuário concluir o recorte.
ESPERA_CAPTURA_SEGUNDOS = 30.0

# Intervalo entre as verificações da área de transferência.
# 0.08 s = 80 ms. Valores menores que isso gastam CPU sem melhorar a resposta.
INTERVALO_VERIFICACAO_SEGUNDOS = 0.08

# Se True, copia o texto reconhecido para a área de transferência.
# Atenção: isso substitui a imagem capturada.
COPIAR_RESULTADO = True

# O OCR do Windows acerta mais em imagens maiores. Capturas cujo maior lado
# seja menor que LADO_ALVO_OCR são ampliadas, respeitando ESCALA_MAXIMA.
LADO_ALVO_OCR = 2500
ESCALA_MAXIMA = 2.0

# Só vale a pena ampliar se o ganho for de pelo menos 20%.
FATOR_MINIMO_DE_AMPLIACAO = 1.2

# A área de transferência pode ficar bloqueada por alguns milissegundos
# enquanto outro programa escreve nela. As operações tentam de novo
# TENTATIVAS_CLIPBOARD vezes, esperando INTERVALO_TENTATIVA_SEGUNDOS.
TENTATIVAS_CLIPBOARD = 5
INTERVALO_TENTATIVA_SEGUNDOS = 0.1
