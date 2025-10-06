import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
from PIL import ImageTk
import os
import sys
# Import converters from the src.models package
from src.models.convert_image import ImageConverter
from src.models.pdf_manager import pdf_to_docx, pdf_to_png, protect_pdf
from src.models.audio_to_text import convert_audio_to_text
from src.models.qrcode_generator import generate_qr_code
from src.models.convert_video import convert_video_choice
from src.models.remove_background import remove_background

def pdf_manager_action():
    """
    Opens a window with options for PDF management: convert to DOCX, convert to PNG, or add password.
    This function is called when the user clicks the "PDF Manager" button in the main menu.
    """
    # Create a new modal window for PDF options
    pdf_win = tk.Toplevel(root)
    pdf_win.title("PDF Manager")
    pdf_win.geometry("320x240")
    pdf_win.resizable(False, False)
    pdf_win.grab_set()  # Makes this window modal (blocks interaction with the main window)

    # Function to convert PDF to DOCX
    def to_docx():
        pdf_win.lift()  # Bring the window to the front
        # Open dialog to select the input PDF
        pdf_file = filedialog.askopenfilename(
            title="Select the PDF file",
            filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")]
        )
        if not pdf_file:
            return  # User cancelled
        # Suggest a default name for the output DOCX file
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        default_docx_name = f"{base_name}.docx"
        # Open dialog to save the DOCX
        docx_file = filedialog.asksaveasfilename(
            title="Save DOCX as",
            defaultextension=".docx",
            initialfile=default_docx_name,
            filetypes=[("DOCX File", "*.docx")]
        )
        if not docx_file:
            return  # User cancelled
        # Call the conversion function and show a success/error message
        success, msg = pdf_to_docx(pdf_file, docx_file)
        if success:
            messagebox.showinfo("Success", msg, parent=pdf_win)
        else:
            messagebox.showerror("Error", msg, parent=pdf_win)

    # Function to convert PDF to PNG images
    def to_png():
        pdf_win.lift()
        # Select the input PDF
        pdf_file = filedialog.askopenfilename(
            title="Select the PDF file",
            filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")]
        )
        if not pdf_file:
            return
        # Select the output folder for the images
        output_dir = filedialog.askdirectory(title="Select the directory to save images")
        if not output_dir:
            return
        # Call the conversion function and show a success/error message
        success, msg = pdf_to_png(pdf_file, output_dir)
        if success:
            messagebox.showinfo("Success", msg, parent=pdf_win)
        else:
            messagebox.showerror("Error", msg, parent=pdf_win)

    # Function to add a password to the PDF
    def add_password():
        pdf_win.lift()
        # Select the input PDF
        pdf_file = filedialog.askopenfilename(
            title="Select the PDF file",
            filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")]
        )
        if not pdf_file:
            return
        # Ask the user for a password (can be left blank)
        password = simpledialog.askstring(
            "PDF Password",
            "Enter a password for the PDF (leave blank for no password):",
            show='*',
            parent=pdf_win
        )
        if password is None:
            return  # User cancelled
        # Select the location to save the protected PDF
        output_pdf = filedialog.asksaveasfilename(
            title="Save protected PDF as",
            defaultextension=".pdf",
            initialfile="protected.pdf",
            filetypes=[("PDF File", "*.pdf")]
        )
        if not output_pdf:
            return
        if password == "":
            # If no password, just copy the PDF
            try:
                with open(pdf_file, "rb") as src, open(output_pdf, "wb") as dst:
                    dst.write(src.read())
                messagebox.showinfo("Success", f"PDF saved without password at: {output_pdf}", parent=pdf_win)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save PDF: {e}", parent=pdf_win)
        else:
            # If a password is provided, protect the PDF
            try:
                protect_pdf(pdf_file, password, output_pdf)
                messagebox.showinfo("Success", f"Protected PDF saved at: {output_pdf}", parent=pdf_win)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to protect PDF: {e}", parent=pdf_win)

    # Layout for the buttons in the PDF Manager window
    ttk.Label(pdf_win, text="Choose a PDF operation:").pack(pady=10)
    ttk.Button(pdf_win, text="Convert PDF to DOCX", command=to_docx).pack(fill="x", padx=30, pady=5)
    ttk.Button(pdf_win, text="Convert PDF to PNG", command=to_png).pack(fill="x", padx=30, pady=5)
    ttk.Button(pdf_win, text="Add Password to PDF", command=add_password).pack(fill="x", padx=30, pady=5)
    ttk.Button(pdf_win, text="Close", command=pdf_win.destroy).pack(fill="x", padx=30, pady=10)

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

    # FIFO: processes files in order of entry
    results = []
    for video_file in videos:
        base_name = os.path.splitext(os.path.basename(video_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}_converted.{output_format}")
        success, msg = convert_video_choice(video_file, output_file, output_format)
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
        # Destroy the conversion window and proceed with the selected conversion type
        conv_win.destroy()
        if conv_type.get() == "single":
            # Pass the selected format to convert_video_choice
            convert_video_choice(root, format_var.get())
        else:
            batch_video_conversion(format_var.get())

    btn_confirm = ttk.Button(conv_win, text="Confirm", command=confirm)
    btn_confirm.pack(pady=10)
    
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def main():
    """
    Initializes the main application window, sets up all converters' buttons and their actions,
    and enters the main GUI event loop.
    """
    global root
    root = tk.Tk()
    root.title("DOTformat - File Converter")
    root.resizable(False, False)

    # Set up the style/theme of the application
    style = ttk.Style()
    style.theme_use('clam')

    # Use resource_path to locate the image
    image_path = resource_path('images/image.png')
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

    btn_remove_bg = ttk.Button(mainframe, text="Remove Image Background", command=remove_background)
    btn_remove_bg.grid(column=0, row=1, pady=5, padx=5, sticky='EW')

    btn_pdf_manager = ttk.Button(mainframe, text="PDF Manager", command=pdf_manager_action)
    btn_pdf_manager.grid(column=0, row=2, pady=5, padx=5, sticky='EW')

    btn_audio_to_text = ttk.Button(mainframe, text="Audio to Text", command=audio_to_text_action)
    btn_audio_to_text.grid(column=0, row=3, pady=5, padx=5, sticky='EW')

    btn_generate_qr_code = ttk.Button(mainframe, text="Generate QR Code", command=qr_code_action)
    btn_generate_qr_code.grid(column=0, row=4, pady=5, padx=5, sticky='EW')

    btn_video_conversion = ttk.Button(mainframe, text="Convert Videos", command=video_conversion_action)
    btn_video_conversion.grid(column=0, row=5, pady=5, padx=5, sticky='EW')

    # Ensure the main frame expands properly
    mainframe.columnconfigure(0, weight=1)

    # Start the GUI main event loop
    root.mainloop()