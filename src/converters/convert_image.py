import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import os
import img2pdf

class ImageConverter:
    def __init__(self, root):
        self.root = root

    def convert_image(self):
        # Create a window for conversion type selection
        choice_window = tk.Toplevel(self.root)
        choice_window.title("Choose Conversion")
        choice_window.geometry("300x150")
        choice_window.resizable(False, False)
        choice_window.grab_set()  # Focus on this window

        def select_format():
            choice_window.destroy()
            self.convert_image_format()

        def select_pdf():
            choice_window.destroy()
            self.convert_images_to_pdf()

        label = ttk.Label(choice_window, text="Select the conversion type:")
        label.pack(pady=10)

        btn_format = ttk.Button(choice_window, text="Convert Image Format", command=select_format)
        btn_format.pack(pady=5, padx=20, fill='x')

        btn_pdf = ttk.Button(choice_window, text="Convert Images to PDF", command=select_pdf)
        btn_pdf.pack(pady=5, padx=20, fill='x')

    def convert_image_format(self):
        # Supported formats
        supported_formats = ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'ico']

        # Allow the user to select one or more images
        image_files = filedialog.askopenfilenames(
            title="Select image(s) to convert",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"), ("All files", "*.*")]
        )

        if not image_files:
            messagebox.showinfo("Information", "No images were selected.")
            return

        # Window for choosing output format
        format_window = tk.Toplevel(self.root)
        format_window.title("Select Output Format")
        format_window.geometry("300x250")
        format_window.resizable(False, False)
        format_window.grab_set()

        label = ttk.Label(format_window, text="Choose the output format:")
        label.pack(pady=10)

        selected_format = tk.StringVar(value=supported_formats[0])
        for fmt in supported_formats:
            rb = ttk.Radiobutton(format_window, text=fmt.upper(), variable=selected_format, value=fmt)
            rb.pack(anchor='w', padx=20)

        def confirm_format():
            output_format = selected_format.get()
            format_window.destroy()
            self.process_conversion(output_format, image_files)

        btn_confirm = ttk.Button(format_window, text="Confirm", command=confirm_format)
        btn_confirm.pack(pady=10)

    def convert_images_to_pdf(self):
        # Allow the user to select multiple images
        image_files = filedialog.askopenfilenames(
            title="Select images to convert to PDF",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"), ("All files", "*.*")]
        )
        if not image_files:
            messagebox.showinfo("Information", "No images were selected.")
            return

        # Suggest a default name for the output PDF
        default_pdf_name = "converted_images.pdf"
        output_pdf_path = filedialog.asksaveasfilename(
            title="Save PDF as",
            defaultextension=".pdf",
            initialfile=default_pdf_name,
            filetypes=[("PDF File", "*.pdf")]
        )
        if not output_pdf_path:
            messagebox.showwarning("Warning", "No save location specified.")
            return

        try:
            # Convert images to PDF without changing dimensions using img2pdf
            with open(output_pdf_path, "wb") as f:
                f.write(img2pdf.convert(image_files))
            messagebox.showinfo("Success", f"PDF created successfully!\nSaved at: {output_pdf_path}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def process_conversion(self, output_format, image_files):
        for file in image_files:
            input_extension = os.path.splitext(file)[1][1:].lower()
            if input_extension == output_format:
                continue  # Skip conversion if input format matches output

            base_name = os.path.splitext(os.path.basename(file))[0]
            input_dir = os.path.dirname(file)
            output_path = os.path.join(input_dir, f"{base_name}.{output_format}")

            if os.path.exists(output_path):
                response = messagebox.askyesno("Overwrite File", f"The file '{output_path}' already exists.\nDo you want to overwrite it?")
                if not response:
                    continue

            try:
                with Image.open(file) as img:
                    # Maintain dimensions and ensure high quality
                    if output_format in ('jpg', 'jpeg'):
                        img.save(output_path, format=output_format.upper(), quality=100, subsampling=0)
                    else:
                        img.save(output_path, format=output_format.upper())
            except Exception as e:
                messagebox.showerror("Error", f"Error converting image '{file}': {e}")
                continue

        messagebox.showinfo("Success", "Conversion completed successfully!")