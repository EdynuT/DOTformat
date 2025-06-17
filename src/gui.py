import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
from PIL import ImageTk
import os
# Import converters
from models.convert_image import ImageConverter
from models.pdf_to_png import pdf_to_png
from models.pdf_to_docx import pdf_to_docx
from models.audio_to_text import convert_audio_to_text
from models.qrcode_generator import generate_qr_code
from models.convert_video import convert_video_choice, convert_video

def pdf_to_png_action():
    """
    Allows the user to select a PDF file and a folder to save the resulting PNG images.
    Calls the pdf_to_png function and shows a message based on the outcome.
    """
    pdf_file = filedialog.askopenfilename(
        title="Select the PDF file",
        filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")]
    )
    if not pdf_file:
        messagebox.showwarning("Warning", "No file selected.")
        return

    output_dir = filedialog.askdirectory(title="Select the directory to save images")
    if not output_dir:
        messagebox.showwarning("Warning", "No directory selected.")
        return

    success, msg = pdf_to_png(pdf_file, output_dir)
    if success:
        messagebox.showinfo("Success", msg)
    else:
        messagebox.showerror("Error", msg)

def pdf_to_word_action():
    """
    Allows the user to choose a PDF file and provide a location/name for the DOCX output.
    Calls the pdf_to_docx function to perform the conversion.
    """
    pdf_file = filedialog.askopenfilename(
        title="Select the PDF file",
        filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")]
    )
    if not pdf_file:
        messagebox.showwarning("Warning", "No file selected.")
        return

    # Derive a default DOCX filename based on the PDF filename
    base_name = os.path.splitext(os.path.basename(pdf_file))[0]
    default_docx_name = f"{base_name}.docx"

    docx_file = filedialog.asksaveasfilename(
        title="Save DOCX as",
        defaultextension=".docx",
        initialfile=default_docx_name,
        filetypes=[("DOCX File", "*.docx")]
    )
    if not docx_file:
        messagebox.showwarning("Warning", "No save location specified.")
        return

    success, msg = pdf_to_docx(pdf_file, docx_file)
    if success:
        messagebox.showinfo("Success", msg)
    else:
        messagebox.showerror("Error", msg)

def audio_to_text_action():
    """
    Allows the user to select an audio file and specify a text file to save the transcription.
    Calls the convert_audio_to_text function and displays a message regarding the conversion.
    """
    audio_file = filedialog.askopenfilename(
        title="Select the audio file",
        filetypes=[("Audio Files", "*.wav;*.mp3;*.flac;*.ogg;*.aac;*.wma;*.m4a;*.mp4;*.webm;*.avi;*.mov;*.3gp"), ("All Files", "*.*")]
    )
    if not audio_file:
        messagebox.showwarning("Warning", "No file selected.")
        return

    # Derive a default text filename from the audio file name
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    default_text_name = f"{base_name}.txt"

    text_file = filedialog.asksaveasfilename(
        title="Save transcription as",
        defaultextension=".txt",
        initialfile=default_text_name,
        filetypes=[("Text File", "*.txt")]
    )
    if not text_file:
        messagebox.showwarning("Warning", "No save location specified.")
        return

    success, msg = convert_audio_to_text(audio_file, text_file)
    if success:
        messagebox.showinfo("Success", msg)
    else:
        messagebox.showerror("Error", msg)

def qr_code_action():
    """
    Prompts the user to input text or a URL to generate a QR code.
    The generated QR code image is then saved to a user specified location.
    """
    text = simpledialog.askstring("Input Text", "Enter text or URL to generate a QR Code:")
    if not text:
        messagebox.showwarning("Warning", "No text or URL provided.")
        return

    save_path = filedialog.asksaveasfilename(
        title="Save QR Code as",
        defaultextension=".png",
        filetypes=[("PNG Image", "*.png")]
    )
    if not save_path:
        messagebox.showwarning("Warning", "No save location specified.")
        return

    success, msg = generate_qr_code(text, save_path)
    if success:
        messagebox.showinfo("Success", msg)
    else:
        messagebox.showerror("Error", msg)

def batch_video_conversion(output_format):
    """
    Performs batch video conversion.
    The user selects a folder containing videos and a destination folder.
    Each video in the folder is converted to the specified output format.
    """
    input_dir = filedialog.askdirectory(title="Select the folder with videos to convert")
    if not input_dir:
        messagebox.showwarning("Warning", "No folder selected.")
        return

    output_dir = filedialog.askdirectory(title="Select the directory to save converted videos")
    if not output_dir:
        messagebox.showwarning("Warning", "No folder selected.")
        return

    # Supported video extensions
    video_extensions = ('.avi', '.mov', '.mkv', '.flv', '.wmv', '.mp4', '.mpeg', '.mpg', '.dav')
    # List all video files from the selected folder
    videos = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(video_extensions)]
    if not videos:
        messagebox.showwarning("Warning", "No videos found in the folder.")
        return

    videos = sorted(videos)  # FIFO: process first file first
    results = []
    for video_file in videos:
        base_name = os.path.splitext(os.path.basename(video_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}_converted.{output_format}")
        success, msg = convert_video(video_file, output_file, output_format)
        results.append(f"{os.path.basename(video_file)}: {'Success' if success else 'Error'}")
    
    summary = "\n".join(results)
    messagebox.showinfo("Conversion Completed", summary)

def video_conversion_action():
    """
    Creates a pop-up window that lets the user choose between:
      - Single video conversion (which will lead to a format-choice dialog), or
      - Batch video conversion, where the user can select the desired output format (MP4, AVI, or MOV)
    """
    # Create a new window for the video conversion options
    conv_win = tk.Toplevel(root)
    conv_win.title("Select Video Conversion Type")
    conv_win.geometry("300x300")
    conv_win.resizable(False, False)
    conv_win.grab_set()  # Make the window modal

    # Label for conversion type
    lbl = ttk.Label(conv_win, text="Choose conversion type:")
    lbl.pack(pady=10)

    # Radio buttons for choosing conversion type: single or batch
    conv_type = tk.StringVar(value="single")
    rb_single = ttk.Radiobutton(conv_win, text="Single Video Conversion", variable=conv_type, value="single")
    rb_single.pack(anchor="w", padx=20)
    rb_batch = ttk.Radiobutton(conv_win, text="Batch Video Conversion", variable=conv_type, value="batch")
    rb_batch.pack(anchor="w", padx=20)

    # For batch conversion, allow the user to choose the output format
    format_var = tk.StringVar(value="mp4")
    lbl_format = ttk.Label(conv_win, text="Select output format for batch conversion:")
    lbl_format.pack(pady=10)
    rb_mp4 = ttk.Radiobutton(conv_win, text="MP4", variable=format_var, value="mp4")
    rb_mp4.pack(anchor="w", padx=40)
    rb_avi = ttk.Radiobutton(conv_win, text="AVI", variable=format_var, value="avi")
    rb_avi.pack(anchor="w", padx=40)
    rb_mov = ttk.Radiobutton(conv_win, text="MOV", variable=format_var, value="mov")
    rb_mov.pack(anchor="w", padx=40)

    def confirm():
        # Destroys the conversion type window and launches the appropriate conversion process
        conv_win.destroy()
        if conv_type.get() == "single":
            # For single conversion use the existing format-choice function
            convert_video_choice(root)
        else:
            # For batch conversion, call the batch conversion function with the selected output format
            batch_video_conversion(format_var.get())

    btn_confirm = ttk.Button(conv_win, text="Confirm", command=confirm)
    btn_confirm.pack(pady=10)

def main():
    """
    Initializes the main application window, sets up all converters' buttons and their actions,
    and enters the main GUI event loop.
    """
    global root  # Declare root as global so it can be accessed by other functions (e.g., video conversion)
    root = tk.Tk()
    root.title("DOTformat - File Converter")
    root.resizable(False, False)

    # Set up the style/theme of the application
    style = ttk.Style()
    style.theme_use('clam')

    # Determine base directory and load the header image
    base_dir = os.path.abspath(os.path.dirname(__file__))
    image_path = os.path.join(base_dir, 'images', 'image.png')
    if not os.path.exists(image_path):
        messagebox.showerror("Error", f"Image not found: {image_path}")
        return

    from PIL import Image
    image = Image.open(image_path)
    photo = ImageTk.PhotoImage(image)

    # Header frame to display the image
    header_frame = ttk.Frame(root)
    header_frame.pack(pady=10)
    image_label = ttk.Label(header_frame, image=photo)
    image_label.image = photo  # Retain a reference to the image to avoid garbage collection
    image_label.pack()

    # Main frame for action buttons
    mainframe = ttk.Frame(root, padding="10 10 10 10")
    mainframe.pack(fill=tk.BOTH, expand=True)

    # Instantiate the ImageConverter class
    image_converter = ImageConverter(root)

    # Create and grid all buttons for the different conversion actions
    btn_convert_image = ttk.Button(mainframe, text="Convert Images", command=image_converter.convert_image)
    btn_convert_image.grid(column=0, row=0, pady=5, padx=5, sticky='EW')

    btn_pdf_to_png = ttk.Button(mainframe, text="PDF to PNG", command=pdf_to_png_action)
    btn_pdf_to_png.grid(column=0, row=1, pady=5, padx=5, sticky='EW')

    btn_pdf_to_word = ttk.Button(mainframe, text="PDF to DOCX", command=pdf_to_word_action)
    btn_pdf_to_word.grid(column=0, row=2, pady=5, padx=5, sticky='EW')

    btn_audio_to_text = ttk.Button(mainframe, text="Audio to Text", command=audio_to_text_action)
    btn_audio_to_text.grid(column=0, row=3, pady=5, padx=5, sticky='EW')

    btn_generate_qr_code = ttk.Button(mainframe, text="Generate QR Code", command=qr_code_action)
    btn_generate_qr_code.grid(column=0, row=4, pady=5, padx=5, sticky='EW')

    # A single combined button for video conversion actions
    btn_video_conversion = ttk.Button(mainframe, text="Convert Videos", command=video_conversion_action)
    btn_video_conversion.grid(column=0, row=5, pady=5, padx=5, sticky='EW')

    # Ensure the main frame expands properly
    mainframe.columnconfigure(0, weight=1)

    # Start the GUI main event loop
    root.mainloop()

if __name__ == "__main__":
    main()