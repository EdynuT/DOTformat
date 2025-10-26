import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import os
import img2pdf
from src.utils.user_settings import get_setting, set_setting
from src.services.conversion_service import ConversionService

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
            initialdir=(get_setting("last_dir_image") or ""),
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"), ("All Files", "*.*")]
        )
        if not image_files:
            # User cancelled the file dialog; do nothing silently.
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
            # Ask once for an output directory
            out_dir = filedialog.askdirectory(
                title="Select output folder",
                initialdir=(get_setting("last_dir_image_out") or get_setting("last_dir_image") or "")
            )
            if not out_dir:
                return
            set_setting("last_dir_image_out", out_dir)
            self.process_conversion(output_format, image_files, out_dir)

        btn_confirm = ttk.Button(format_window, text="Confirm", command=confirm_format)
        btn_confirm.pack(pady=10)

    def convert_images_to_pdf(self):
        """
        Prompts the user to select multiple images and then combines them into a single PDF file.
        """
        image_files = filedialog.askopenfilenames(
            title="Select images to convert to PDF",
            initialdir=(get_setting("last_dir_image") or ""),
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"), ("All Files", "*.*")]
        )
        if not image_files:
            # User cancelled the file dialog; do nothing silently.
            return

        # Suggest a default PDF name
        if len(image_files) == 1:
            pdf_name = os.path.splitext(os.path.basename(image_files[0]))[0] + ".pdf"
        else:
            pdf_name = "merged_images.pdf"
            
        set_setting("last_dir_image", os.path.dirname(image_files[0]))
        output_pdf_path = filedialog.asksaveasfilename(
            title="Save PDF as",
            defaultextension=".pdf",
            initialfile=pdf_name,
            initialdir=(get_setting("last_dir_image") or ""),
            filetypes=[("PDF File", "*.pdf")]
        )
        if not output_pdf_path:
            # User cancelled the save dialog; do nothing silently.
            return

        # Preprocess images: flatten alpha channels (img2pdf refuses images with alpha)
        tmp_paths = []
        def _prepare_no_alpha(path: str) -> str:
            try:
                with Image.open(path) as im:
                    if im.mode in ("RGBA", "LA") or (im.mode == "P" and 'transparency' in im.info):
                        rgb = Image.new("RGB", im.size, (255, 255, 255))
                        if im.mode != "RGBA":
                            im = im.convert("RGBA")
                        rgb.paste(im, mask=im.split()[3])
                        import tempfile
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                        tmp_paths.append(tmp.name); tmp.close()
                        rgb.save(tmp.name, format='JPEG', quality=95)
                        return tmp.name
            except Exception:
                pass
            return path

        prepared = [_prepare_no_alpha(p) for p in image_files]

        try:
            with open(output_pdf_path, "wb") as f:
                f.write(img2pdf.convert(prepared))
            messagebox.showinfo("Success", f"PDF created successfully!\nSaved at: {output_pdf_path}")
            try:
                # Log with first image as input exemplar
                first_input = image_files[0] if image_files else None
                ConversionService().log_success("images_to_pdf", first_input, output_pdf_path)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Error", f"Error during conversion: {e}")
            try:
                first_input = image_files[0] if image_files else None
                ConversionService().log_error("images_to_pdf", first_input, str(e))
            except Exception:
                pass
        finally:
            for p in tmp_paths:
                try: os.remove(p)
                except Exception: pass

    def process_conversion(self, output_format, image_files, out_dir):
        """
        Converts each selected image into the chosen output format.
        If an output file already exists, asks the user whether to overwrite it.
        """
        # Simple determinate progress window
        prog = tk.Toplevel(self.root)
        prog.title("Converting images")
        prog.geometry("360x110")
        prog.resizable(False, False)
        prog.grab_set()
        ttk.Label(prog, text=f"Converting to {output_format.upper()}...").pack(pady=(10,4))
        var = tk.DoubleVar(value=0.0)
        bar = ttk.Progressbar(prog, mode='determinate', maximum=100, variable=var, length=300)
        bar.pack(pady=8)

        total = len(image_files)
        done = 0
        converted = 0
        errors: list[str] = []
        logger = ConversionService()

        for file in image_files:
            input_extension = os.path.splitext(file)[1][1:].lower()
            if input_extension == output_format:
                continue  # Skip if already in desired format

            base_name = os.path.splitext(os.path.basename(file))[0]
            output_path = os.path.join(out_dir, f"{base_name}.{output_format}")

            if os.path.exists(output_path):
                response = messagebox.askyesno("Overwrite File", f"{output_path} already exists.\nOverwrite?")
                if not response:
                    continue

            try:
                with Image.open(file) as img:
                    fmt = output_format.lower()
                    if fmt in ('jpg', 'jpeg'):
                        # Ensure no alpha channel: flatten onto white background if needed
                        if img.mode in ("RGBA", "LA") or (img.mode == "P" and 'transparency' in img.info):
                            img = img.convert("RGBA")
                            bg = Image.new("RGB", img.size, (255, 255, 255))
                            bg.paste(img, mask=img.split()[3])
                            img = bg
                        else:
                            img = img.convert("RGB")
                        img.save(output_path, format='JPEG', quality=100, subsampling=0, optimize=True)
                    else:
                        # For formats supporting alpha, keep original mode
                        img.save(output_path, format=output_format.upper())
                    converted += 1
                    try:
                        logger.log_success("image_convert", file, output_path)
                    except Exception:
                        pass
            except Exception as e:
                errors.append(f"{os.path.basename(file)}: {e}")
                try:
                    logger.log_error("image_convert", file, str(e))
                except Exception:
                    pass
            finally:
                done += 1
                pct = (done/total) * 100.0
                try:
                    var.set(pct); bar.update_idletasks()
                except Exception:
                    pass

        try:
            prog.destroy()
        except Exception:
            pass

        if errors and converted == 0:
            messagebox.showerror("Error", "No images were converted.\n" + "\n".join(errors[:5]))
        elif errors:
            messagebox.showwarning("Partial Success", f"Converted {converted}/{total} images. Some failed:\n" + "\n".join(errors[:5]))
        else:
            messagebox.showinfo("Success", f"Converted {converted}/{total} images successfully!")