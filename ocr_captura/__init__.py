"""Lógica do OCR de capturas de tela no Windows.

O ponto de entrada continua sendo o `app.py`, na raiz do projeto. Este pacote
guarda as partes internas, separadas por responsabilidade:

- configuracao.py: valores que você pode ajustar;
- imagens.py: conversão e ampliação de imagens;
- area_transferencia.py: leitura/escrita da área de transferência;
- ocr.py: integração com o OCR nativo do Windows;
- atalhos.py: atalhos globais de teclado;
- captura.py: laço principal que liga todas as peças.
"""
