import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import os
import img2pdf

class ImageConverter:
    """
    A class for converting images by either changing image formats or merging them into a single PDF.
    """
    def __init__(self, root):
        """
        Initializes the ImageConverter with the given Tkinter root.
        """
        self.root = root

    def convert_image(self):
        """
        Opens a dialog for the user to choose the type of image conversion:
          - Format conversion (e.g., JPG to PNG)
          - Combining images into a PDF
        """
        # Create a pop-up window for conversion type selection
        choice_window = tk.Toplevel(self.root)
        choice_window.title("Choose Conversion Type")
        choice_window.geometry("300x150")
        choice_window.resizable(False, False)
        choice_window.grab_set()  # Keep focus on this window

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
        """
        Allows the user to select one or more images, choose an output format,
        and then converts the images to that format.
        """
        supported_formats = ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'ico']

        # Prompt the user to select image files
        image_files = filedialog.askopenfilenames(
            title="Select images to convert",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"), ("All Files", "*.*")]
        )
        if not image_files:
            messagebox.showinfo("Information", "No images selected.")
            return

        # Create a window to choose the desired output format
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
        """
        Prompts the user to select multiple images and then combines them into a single PDF file.
        """
        image_files = filedialog.askopenfilenames(
            title="Select images to convert to PDF",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"), ("All Files", "*.*")]
        )
        if not image_files:
            messagebox.showinfo("Information", "No images selected.")
            return

        # Suggest a default PDF name
        if len(image_files) == 1:
            pdf_name = os.path.splitext(os.path.basename(image_files[0]))[0] + ".pdf"
        else:
            pdf_name = "merged_images.pdf"
            
        output_pdf_path = filedialog.asksaveasfilename(
            title="Save PDF as",
            defaultextension=".pdf",
            initialfile=pdf_name,
            filetypes=[("PDF File", "*.pdf")]
        )
        if not output_pdf_path:
            messagebox.showwarning("Warning", "No save location specified.")
            return

        try:
            with open(output_pdf_path, "wb") as f:
                f.write(img2pdf.convert(image_files))
            messagebox.showinfo("Success", f"PDF created successfully!\nSaved at: {output_pdf_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error during conversion: {e}")

    def process_conversion(self, output_format, image_files):
        """
        Converts each selected image into the chosen output format.
        If an output file already exists, asks the user whether to overwrite it.
        """
        for file in image_files:
            input_extension = os.path.splitext(file)[1][1:].lower()
            if input_extension == output_format:
                continue  # Skip if already in desired format

            base_name = os.path.splitext(os.path.basename(file))[0]
            input_dir = os.path.dirname(file)
            output_path = os.path.join(input_dir, f"{base_name}.{output_format}")

            if os.path.exists(output_path):
                response = messagebox.askyesno("Overwrite File", f"{output_path} already exists.\nOverwrite?")
                if not response:
                    continue

            try:
                with Image.open(file) as img:
                    # Save image; for JPEG, ensure high quality
                    if output_format in ('jpg', 'jpeg'):
                        img.save(output_path, format=output_format.upper(), quality=100, subsampling=0)
                    else:
                        img.save(output_path, format=output_format.upper())
            except Exception as e:
                messagebox.showerror("Error", f"Error converting {file}: {e}")
                continue

        messagebox.showinfo("Success", "Image conversion completed successfully!")