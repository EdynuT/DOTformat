import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
from PIL import ImageTk
import os
from conversores.convert_image import ImageConverter
from conversores.pdf_to_png import pdf_to_png
from conversores.pdf_to_word import pdf_to_word
from conversores.audio_to_text import convert_audio_to_text
from conversores.qrcode_generator import generate_qr_code
from conversores.video_to_mp4 import convert_video_to_mp4

def pdf_to_png_action():
    pdf_file = filedialog.askopenfilename(
        title="Selecione o arquivo PDF",
        filetypes=[("Arquivo PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
    )
    if not pdf_file:
        messagebox.showwarning("Aviso", "Nenhum arquivo selecionado.")
        return

    output_dir = filedialog.askdirectory(title="Selecione o diretório para salvar as imagens")
    if not output_dir:
        messagebox.showwarning("Aviso", "Nenhum diretório selecionado.")
        return

    success, message = pdf_to_png(pdf_file, output_dir)
    if success:
        messagebox.showinfo("Sucesso", message)
    else:
        messagebox.showerror("Erro", message)

def pdf_to_word_action():
    pdf_file = filedialog.askopenfilename(
        title="Selecione o arquivo PDF",
        filetypes=[("Arquivo PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
    )
    if not pdf_file:
        messagebox.showwarning("Aviso", "Nenhum arquivo selecionado.")
        return

    base_name = os.path.splitext(os.path.basename(pdf_file))[0]
    default_docx_name = f"{base_name}.docx"

    docx_file = filedialog.asksaveasfilename(
        title="Salvar DOCX como",
        defaultextension=".docx",
        initialfile=default_docx_name,
        filetypes=[("Arquivo DOCX", "*.docx")]
    )
    if not docx_file:
        messagebox.showwarning("Aviso", "Nenhum local de salvamento especificado.")
        return

    success, message = pdf_to_word(pdf_file, docx_file)
    if success:
        messagebox.showinfo("Sucesso", message)
    else:
        messagebox.showerror("Erro", message)

def audio_to_text_action():
    audio_file = filedialog.askopenfilename(
        title="Selecione o arquivo de áudio",
        filetypes=[("Arquivos de Áudio", "*.wav;*.mp3;*.flac;*.ogg;*.aac;*.wma;*.m4a;*.mp4;*.webm;*.avi;*.mov;*.3gp"), ("Todos os arquivos", "*.*")]
    )
    if not audio_file:
        messagebox.showwarning("Aviso", "Nenhum arquivo selecionado.")
        return

    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    default_text_name = f"{base_name}.txt"

    text_file = filedialog.asksaveasfilename(
        title="Salvar transcrição como",
        defaultextension=".txt",
        initialfile=default_text_name,
        filetypes=[("Arquivo de Texto", "*.txt")]
    )
    if not text_file:
        messagebox.showwarning("Aviso", "Nenhum local de salvamento especificado.")
        return

    success, message = convert_audio_to_text(audio_file, text_file)
    if success:
        messagebox.showinfo("Sucesso", message)
    else:
        messagebox.showerror("Erro", message)

def qr_code_action():
    text = simpledialog.askstring("Entrada de Texto", "Digite o texto ou URL para gerar o QR Code:")
    if not text:
        messagebox.showwarning("Aviso", "Nenhum texto ou URL fornecido.")
        return

    save_path = filedialog.asksaveasfilename(
        title="Salvar QR Code como",
        defaultextension=".png",
        filetypes=[("Imagem PNG", "*.png")]
    )
    if not save_path:
        messagebox.showwarning("Aviso", "Nenhum local de salvamento especificado.")
        return

    success, message = generate_qr_code(text, save_path)
    if success:
        messagebox.showinfo("Sucesso", message)
    else:
        messagebox.showerror("Erro", message)

def video_to_mp4_action():
    video_file = filedialog.askopenfilename(
        title="Selecione o arquivo de vídeo",
        filetypes=[("Arquivos de Vídeo", "*.avi;*.mov;*.mkv;*.flv;*.wmv;*.mp4;*.mpeg;*.mpg"), ("Todos os arquivos", "*.*")]
    )
    if not video_file:
        messagebox.showwarning("Aviso", "Nenhum arquivo selecionado.")
        return

    base_name = os.path.splitext(os.path.basename(video_file))[0]
    default_output = f"{base_name}_converted.mp4"
    output_file = filedialog.asksaveasfilename(
        title="Salvar vídeo convertido como",
        defaultextension=".mp4",
        initialfile=default_output,
        filetypes=[("Arquivo MP4", "*.mp4")]
    )
    if not output_file:
        messagebox.showwarning("Aviso", "Nenhum local de salvamento especificado.")
        return

    success, message = convert_video_to_mp4(video_file, output_file)
    if success:
        messagebox.showinfo("Sucesso", message)
    else:
        messagebox.showerror("Erro", message)

def video_queue_conversion_action():
    # Seleciona a pasta onde os vídeos estão (fila de conversão)
    input_dir = filedialog.askdirectory(title="Selecione a pasta com os vídeos a converter")
    if not input_dir:
        messagebox.showwarning("Aviso", "Nenhuma pasta selecionada.")
        return

    # Seleciona a pasta de destino para os vídeos convertidos
    output_dir = filedialog.askdirectory(title="Selecione o diretório para salvar os vídeos convertidos")
    if not output_dir:
        messagebox.showwarning("Aviso", "Nenhum diretório selecionado.")
        return

    # Define as extensões de vídeo suportadas, incluindo DAV
    video_extensions = ('.avi', '.mov', '.mkv', '.flv', '.wmv', '.mp4', '.mpeg', '.mpg', '.dav')
    # Pega os arquivos e ordena em ordem alfabética
    videos = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(video_extensions)]
    if not videos:
        messagebox.showwarning("Aviso", "Nenhum vídeo encontrado na pasta.")
        return

    videos = sorted(videos)  # FIFO: primeiro inserido, primeiro processado

    resultados = []
    for video_file in videos:
        base_name = os.path.splitext(os.path.basename(video_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}_converted.mp4")
        success, msg = convert_video_to_mp4(video_file, output_file)
        resultados.append(f"{os.path.basename(video_file)}: {'Sucesso' if success else 'Erro'}")
    
    resumo = "\n".join(resultados)
    messagebox.showinfo("Conversão Finalizada", resumo)

def main():
    root = tk.Tk()
    root.title("DOTformat - Conversor de Arquivos")
    root.resizable(False, False)

    style = ttk.Style()
    style.theme_use('clam')

    base_dir = os.path.abspath(os.path.dirname(__file__))
    image_path = os.path.join(base_dir, 'images', 'image.png')
    if not os.path.exists(image_path):
        messagebox.showerror("Erro", f"Imagem não encontrada: {image_path}")
        return

    from PIL import Image
    image = Image.open(image_path)
    photo = ImageTk.PhotoImage(image)

    header_frame = ttk.Frame(root)
    header_frame.pack(pady=10)

    image_label = ttk.Label(header_frame, image=photo)
    image_label.image = photo
    image_label.pack()

    mainframe = ttk.Frame(root, padding="10 10 10 10")
    mainframe.pack(fill=tk.BOTH, expand=True)

    image_converter = ImageConverter(root)

    btn_convert_image = ttk.Button(mainframe, text="Converter Imagens", command=image_converter.convert_image)
    btn_convert_image.grid(column=0, row=0, pady=5, padx=5, sticky='EW')

    btn_pdf_to_png = ttk.Button(mainframe, text="PDF para PNG", command=pdf_to_png_action)
    btn_pdf_to_png.grid(column=0, row=1, pady=5, padx=5, sticky='EW')

    btn_pdf_to_word = ttk.Button(mainframe, text="PDF para Word", command=pdf_to_word_action)
    btn_pdf_to_word.grid(column=0, row=2, pady=5, padx=5, sticky='EW')

    btn_audio_to_text = ttk.Button(mainframe, text="Áudio para Texto", command=audio_to_text_action)
    btn_audio_to_text.grid(column=0, row=3, pady=5, padx=5, sticky='EW')

    btn_generate_qr_code = ttk.Button(mainframe, text="Gerar QR Code", command=qr_code_action)
    btn_generate_qr_code.grid(column=0, row=4, pady=5, padx=5, sticky='EW')

    btn_video_to_mp4 = ttk.Button(mainframe, text="Vídeo para MP4", command=video_to_mp4_action)
    btn_video_to_mp4.grid(column=0, row=5, pady=5, padx=5, sticky='EW')

    btn_video_queue = ttk.Button(mainframe, text="Fila de Vídeos para MP4", command=video_queue_conversion_action)
    btn_video_queue.grid(column=0, row=6, pady=5, padx=5, sticky='EW')

    mainframe.columnconfigure(0, weight=1)

    root.mainloop()

if __name__ == "__main__":
    main()