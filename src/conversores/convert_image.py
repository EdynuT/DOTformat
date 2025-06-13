import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import os
import img2pdf

class ImageConverter:
    def __init__(self, root):
        self.root = root

    def convert_image(self):
        # Cria a janela para a escolha
        escolha_window = tk.Toplevel(self.root)
        escolha_window.title("Escolha a Conversão")
        escolha_window.geometry("300x150")
        escolha_window.resizable(False, False)
        escolha_window.grab_set()  # Foca na janela atual

        def selecionar_formato():
            escolha_window.destroy()
            self.convert_image_format()

        def selecionar_pdf():
            escolha_window.destroy()
            self.convert_images_to_pdf()

        label = ttk.Label(escolha_window, text="Selecione o tipo de conversão:")
        label.pack(pady=10)

        btn_formato = ttk.Button(escolha_window, text="Converter Formato de Imagem", command=selecionar_formato)
        btn_formato.pack(pady=5, padx=20, fill='x')

        btn_pdf = ttk.Button(escolha_window, text="Converter Imagens para PDF", command=selecionar_pdf)
        btn_pdf.pack(pady=5, padx=20, fill='x')

    def convert_image_format(self):
        # Formatos suportados
        formatos_suportados = ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'ico']

        # Permitir ao usuário selecionar uma ou mais imagens
        image_files = filedialog.askopenfilenames(
            title="Selecione a(s) imagem(ns) para converter",
            filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"), ("Todos os arquivos", "*.*")]
        )

        if not image_files:
            messagebox.showinfo("Informação", "Nenhuma imagem foi selecionada.")
            return

        # Janela para seleção do formato de saída
        formato_window = tk.Toplevel(self.root)
        formato_window.title("Selecione o Formato de Saída")
        formato_window.geometry("300x250")
        formato_window.resizable(False, False)
        formato_window.grab_set()

        label = ttk.Label(formato_window, text="Escolha o formato de saída:")
        label.pack(pady=10)

        selected_format = tk.StringVar(value=formatos_suportados[0])

        for fmt in formatos_suportados:
            rb = ttk.Radiobutton(formato_window, text=fmt.upper(), variable=selected_format, value=fmt)
            rb.pack(anchor='w', padx=20)

        def confirmar_formato():
            output_format = selected_format.get()
            formato_window.destroy()
            self.processar_conversao(output_format, image_files)

        btn_confirmar = ttk.Button(formato_window, text="Confirmar", command=confirmar_formato)
        btn_confirmar.pack(pady=10)

    def convert_images_to_pdf(self):
        # Permite ao usuário selecionar múltiplas imagens
        image_files = filedialog.askopenfilenames(
            title="Selecione as imagens para converter em PDF",
            filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"), ("Todos os arquivos", "*.*")]
        )
        if not image_files:
            messagebox.showinfo("Informação", "Nenhuma imagem foi selecionada.")
            return

        # Sugerir um nome padrão para o PDF de saída
        default_pdf_name = "imagens_convertidas.pdf"
        output_pdf_path = filedialog.asksaveasfilename(
            title="Salvar PDF como",
            defaultextension=".pdf",
            initialfile=default_pdf_name,
            filetypes=[("Arquivo PDF", "*.pdf")]
        )
        if not output_pdf_path:
            messagebox.showwarning("Aviso", "Nenhum local de salvamento especificado.")
            return

        try:
            # Converte as imagens para PDF sem alterar o tamanho usando img2pdf
            with open(output_pdf_path, "wb") as f:
                f.write(img2pdf.convert(image_files))
            messagebox.showinfo("Sucesso", f"PDF criado com sucesso!\nSalvo em: {output_pdf_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")

    def processar_conversao(self, output_format, image_files):
        for file in image_files:
            input_extension = os.path.splitext(file)[1][1:].lower()
            if input_extension == output_format:
                continue  # Pula a conversão se o formato de entrada for igual ao de saída

            base_name = os.path.splitext(os.path.basename(file))[0]
            input_dir = os.path.dirname(file)
            output_path = os.path.join(input_dir, f"{base_name}.{output_format}")

            if os.path.exists(output_path):
                resposta = messagebox.askyesno("Sobrescrever arquivo", f"O arquivo '{output_path}' já existe.\nDeseja sobrescrevê-lo?")
                if not resposta:
                    continue  # Pula para a próxima imagem

            try:
                with Image.open(file) as img:
                    # Manter as dimensões e especificar qualidade máxima
                    if output_format in ('jpg', 'jpeg'):
                        img.save(output_path, format=output_format.upper(), quality=100, subsampling=0)
                    else:
                        img.save(output_path, format=output_format.upper())
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao converter a imagem '{file}': {e}")
                continue  # Continua com a próxima imagem

        messagebox.showinfo("Sucesso", "Conversão concluída com sucesso!")