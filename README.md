# DOTFORMAT

## Visão Geral

O **DOTFORMAT** é um projeto desenvolvido por Edynu para lidar com várias tarefas de conversão e manipulação de arquivos de forma totalmente gratuita e de livre acesso, como:

- **Conversão de Áudio para Texto**: Transforme arquivos de áudio em texto usando reconhecimento de voz.

- **Conversão de Imagens**: Converta imagens para diferentes formatos e resoluções.

- **PDF para PNG**: Converta documentos PDF em imagens PNG para visualização fácil.

- **PDF para Word**: Converta PDF para documentos Word editáveis.

- **Gerador de QR codes**: Cria QR codes a partir do texto inserido.

- **Senhas para PDFs**: Gera uma senha para um arquivo de PDF escolhido para uma melhor segurança.

- **Videos para MP4**: Transforma vídeos de qualquer formato em MP4 para melhor utilização. 
(Esse script usa mais de CPU e memória RAM do que o normal, então espere um pouco mais de lentitão ao usá-lo)

## Estrutura do Projeto

A estrutura do projeto está organizada da seguinte forma:

```sh
DOTFORMAT/
├── ffmpeg/                   # Binários do FFmpeg
├── src/
│   ├──__pycache__/
│   ├── conversores/          # Módulos de conversão de arquivos
│   │   ├── __init__.py
│   │   ├── audio_to_text.py
│   │   ├── convert_image.py
│   │   ├── pdf_to_png.py
│   │   ├── pdf_to_word.py
│   │   ├── qrcode_generator.py
│   │   ├── senha_pdf.py
│   │   └── video_to_mp4.py
│   ├──images/                # Recursos de imagem
│   │   ├──image.ico          # Capa do atalho na área de trabalho
│   │   └──image.png          # Imagem para a interface do executável
│   ├── gui.py                # Interface gráfica do usuário
│   └── steup.py              # Cria o ambiente virtual e instala todas as dependencias
├── DOTformat.spec            # Arquivo de especificação para build do projeto
├── requirements.txt          # Lista de bibliotecas Python necessárias para o funcionamento
├── LICENCE                   # licença do projeto
└── README.md                 # Documentação do projeto
```

## Instalação
Siga os passos abaixo para configurar o ambiente, instalar as dependências necessárias e criar o arquivo executável:

- Clone o repositório:

```sh
git clone https://github.com/EdynuT/DOTformat.git
cd DOTformat
```

- No terminal escreva:

```sh
python setup.py
```

Dessa forma o programa deve ser instalado sem maiores problemas

## Alterações

- Caso seja feita alguma alteração não oficial no projeto (como a adição de um novo script), recomendo que atualize o arquivo .spec:

```sh
cd DOTformat
pyi-makespec --name DOTformat --onefile --windowed src\gui.py
```

- Em seguida crie o executável:

```sh
pyinstaller DOTformat.spec
```