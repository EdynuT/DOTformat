import os
import PyPDF2
import random
from tkinter import Tk
from tkinter.filedialog import askopenfilename

def gerar_senha():
    return str(random.randint(10000, 99999))

def proteger_pdf(input_pdf, output_pdf, senha):
    # Abrir o arquivo PDF de entrada
    pdf_reader = PyPDF2.PdfReader(input_pdf)
    pdf_writer = PyPDF2.PdfWriter()
    
    # Adicionar todas as páginas ao writer
    for page_num in range(len(pdf_reader.pages)):
        pdf_writer.add_page(pdf_reader.pages[page_num])
    
    # Definir a senha do PDF
    pdf_writer.encrypt(senha)
    
    # Escrever o PDF protegido no arquivo de saída
    with open(output_pdf, "wb") as pdf_out:
        pdf_writer.write(pdf_out)

# Exemplo de uso
Tk().withdraw()  # Esconder a janela principal do tkinter
input_pdf = askopenfilename(title="Selecione o arquivo PDF")
if not input_pdf:
    print("Nenhum arquivo selecionado. O script será encerrado.")
else:
    output_pdf = os.path.join(os.path.dirname(input_pdf), "arquivo_protegido.pdf")
    senha = gerar_senha()
    print(f"A senha gerada para o PDF é: {senha}")
    proteger_pdf(input_pdf, output_pdf, senha)
    print(f"PDF protegido salvo em: {output_pdf}")
