import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import warnings
import os
import img2pdf
from src.utils.user_settings import get_setting, set_setting
from src.services.conversion_service import ConversionService
from src.models import svg_converter
from src.gui.widgets.progress import run_with_progress_status

class ImageConverter:
    """
    A class for converting images by either changing image formats or merging them into a single PDF.
    """
    def __init__(self, root):
        """
        Initializes the ImageConverter with the given Tkinter root.
        """
        self.root = root

    # Allow very large images by disabling Pillow's decompression bomb limit and warning.
    try:
        Image.MAX_IMAGE_PIXELS = None  # Remove safety cap (use with caution)
        warnings.simplefilter('ignore', Image.DecompressionBombWarning)
    except Exception:
        pass

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
        supported_formats = ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'ico', 'svg']

        # Prompt the user to select image files. SVG is accepted as an input too
        # (it is rendered back to a raster format).
        image_files = filedialog.askopenfilenames(
            title="Select images to convert",
            initialdir=(get_setting("last_dir_image") or ""),
            filetypes=[
                ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico;*.webp;*.tiff;*.tif;*.svg"),
                ("All Files", "*.*"),
            ]
        )
        if not image_files:
            # User cancelled the file dialog; do nothing silently.
            return

        set_setting("last_dir_image", os.path.dirname(image_files[0]))

        # Create a window to choose the desired output format
        format_window = tk.Toplevel(self.root)
        format_window.title("Select Output Format")
        format_window.geometry("320x290")
        format_window.resizable(False, False)
        format_window.grab_set()

        label = ttk.Label(format_window, text="Choose the output format:")
        label.pack(pady=10)

        selected_format = tk.StringVar(value=supported_formats[0])
        for fmt in supported_formats:
            text = "SVG (vector)" if fmt == 'svg' else fmt.upper()
            rb = ttk.Radiobutton(format_window, text=text, variable=selected_format, value=fmt)
            rb.pack(anchor='w', padx=20)

        def confirm_format():
            output_format = selected_format.get()
            format_window.destroy()

            # Vectorising needs its own settings, asked before the output folder
            # so the user can still back out cheaply.
            trace_opts = None
            if output_format == 'svg':
                if not svg_converter.vtracer_available():
                    messagebox.showerror(
                        "SVG unavailable",
                        "SVG output needs the 'vtracer' package.\n\n"
                        "Install it with:  pip install vtracer"
                    )
                    return
                trace_opts = self.ask_svg_options()
                if trace_opts is None:
                    return

            # Ask once for an output directory
            out_dir = filedialog.askdirectory(
                title="Select output folder",
                initialdir=(get_setting("last_dir_image_out") or get_setting("last_dir_image") or "")
            )
            if not out_dir:
                return
            set_setting("last_dir_image_out", out_dir)
            if output_format == 'svg':
                self.process_vectorization(image_files, out_dir, trace_opts)
            else:
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

    def ask_svg_options(self):
        """Ask how to trace, returning a TraceOptions or None if cancelled.

        Presets cover the three kinds of image people actually bring; the
        Advanced panel stays collapsed but exposes the same values for anyone
        who wants to tune a stubborn image.
        """
        win = tk.Toplevel(self.root)
        win.title("Convert to SVG")
        win.resizable(False, False)
        win.grab_set()
        try:
            win.transient(self.root)
        except Exception:
            pass

        result = {'opts': None}

        ttk.Label(win, text="What kind of image is this?").pack(anchor='w', padx=16, pady=(14, 6))

        preset_var = tk.StringVar(value='logo')
        hints = {
            'logo': "Flat colours and sharp edges. Smallest, cleanest files.",
            'illustration': "Balanced: about half the file size of Detailed photo.",
            'photo': "Keeps the most detail. Slower, and much larger files.",
        }
        for key in ('logo', 'illustration', 'photo'):
            ttk.Radiobutton(
                win, text=svg_converter.PRESET_LABELS[key], variable=preset_var, value=key
            ).pack(anchor='w', padx=24)
            ttk.Label(win, text=hints[key], foreground="#666").pack(anchor='w', padx=46, pady=(0, 4))

        bw_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(win, text="Black and white", variable=bw_var).pack(anchor='w', padx=24, pady=(4, 0))

        # --- Advanced (collapsed by default) ---
        adv_shown = {'on': False}
        adv_frame = ttk.Frame(win)

        vars_ = {
            'snap': tk.BooleanVar(value=True),
            'colors': tk.IntVar(value=8),
            'filter_speckle': tk.IntVar(value=16),
            'color_precision': tk.IntVar(value=6),
            'layer_difference': tk.IntVar(value=48),
            'path_precision': tk.IntVar(value=3),
            'curve': tk.StringVar(value='spline'),
            'denoise': tk.IntVar(value=0),
        }

        def load_preset(*_):
            opts = svg_converter.PRESETS[preset_var.get()]
            vars_['snap'].set(bool(opts.colors))
            vars_['colors'].set(opts.colors or 8)
            vars_['filter_speckle'].set(opts.filter_speckle)
            vars_['color_precision'].set(opts.color_precision)
            vars_['layer_difference'].set(opts.layer_difference)
            vars_['path_precision'].set(opts.path_precision)
            vars_['curve'].set(opts.mode)
            vars_['denoise'].set(opts.denoise)

        preset_var.trace_add('write', load_preset)
        load_preset()

        ttk.Checkbutton(
            adv_frame,
            text="Snap similar colours together (removes fuzzy edges)",
            variable=vars_['snap'],
        ).grid(row=0, column=0, columnspan=2, sticky='w', pady=(4, 6))

        spins = [
            ("Colours to keep", 'colors', 2, 256),
            ("Discard specks smaller than", 'filter_speckle', 0, 128),
            ("Colour precision", 'color_precision', 1, 8),
            ("Layer difference", 'layer_difference', 0, 128),
            ("Coordinate precision", 'path_precision', 1, 8),
            # Off by default on purpose: it rescues a heavily compressed JPEG and
            # flattens the texture of a lightly compressed one, so it is the
            # user's call, not a default. 1 is the measured sweet spot.
            ("Reduce JPEG artifacts (0 = off)", 'denoise', 0, 10),
        ]
        for row, (text, key, lo, hi) in enumerate(spins, start=1):
            ttk.Label(adv_frame, text=text).grid(row=row, column=0, sticky='w', pady=2)
            ttk.Spinbox(
                adv_frame, from_=lo, to=hi, textvariable=vars_[key], width=6
            ).grid(row=row, column=1, sticky='e', padx=(12, 0))

        ttk.Label(adv_frame, text="Curves").grid(row=len(spins) + 1, column=0, sticky='w', pady=(6, 2))
        curve_box = ttk.Frame(adv_frame)
        curve_box.grid(row=len(spins) + 1, column=1, sticky='e')
        ttk.Radiobutton(curve_box, text="Smooth", variable=vars_['curve'], value='spline').pack(side='left')
        ttk.Radiobutton(curve_box, text="Straight", variable=vars_['curve'], value='polygon').pack(side='left')

        adv_btn = ttk.Button(win, text="▸ Advanced")

        def toggle_adv():
            adv_shown['on'] = not adv_shown['on']
            if adv_shown['on']:
                adv_btn.config(text="▾ Advanced")
                adv_frame.pack(fill='x', padx=24, pady=(0, 4), before=button_row)
            else:
                adv_btn.config(text="▸ Advanced")
                adv_frame.pack_forget()

        adv_btn.config(command=toggle_adv)
        adv_btn.pack(anchor='w', padx=20, pady=(10, 0))

        button_row = ttk.Frame(win)
        button_row.pack(fill='x', padx=16, pady=12)

        def confirm():
            base = svg_converter.PRESETS[preset_var.get()]
            try:
                result['opts'] = svg_converter.TraceOptions(
                    colors=(int(vars_['colors'].get()) if vars_['snap'].get() else None),
                    hard_alpha=base.hard_alpha,
                    colormode=('binary' if bw_var.get() else 'color'),
                    hierarchical=base.hierarchical,
                    mode=vars_['curve'].get(),
                    filter_speckle=int(vars_['filter_speckle'].get()),
                    color_precision=int(vars_['color_precision'].get()),
                    layer_difference=int(vars_['layer_difference'].get()),
                    corner_threshold=base.corner_threshold,
                    length_threshold=base.length_threshold,
                    max_iterations=base.max_iterations,
                    splice_threshold=base.splice_threshold,
                    path_precision=int(vars_['path_precision'].get()),
                    denoise=int(vars_['denoise'].get()),
                )
            except (tk.TclError, ValueError):
                messagebox.showerror("Invalid settings", "Please check the advanced values.", parent=win)
                return
            win.destroy()

        ttk.Button(button_row, text="Cancel", command=win.destroy).pack(side='right')
        ttk.Button(button_row, text="Convert", command=confirm).pack(side='right', padx=(0, 8))

        win.bind('<Return>', lambda _e: confirm())
        self.root.wait_window(win)
        return result['opts']

    def process_vectorization(self, image_files, out_dir, opts):
        """Trace each selected raster image into an SVG."""
        # Overwrite prompts must happen before the worker starts: a background
        # thread cannot open Tk dialogs.
        jobs = []
        for file in image_files:
            if os.path.splitext(file)[1][1:].lower() == 'svg':
                continue  # already vector; nothing to trace
            base_name = os.path.splitext(os.path.basename(file))[0]
            output_path = os.path.join(out_dir, f"{base_name}.svg")
            if os.path.exists(output_path):
                if not messagebox.askyesno(
                    "Overwrite File", f"{output_path} already exists.\nOverwrite?"
                ):
                    continue
            jobs.append((file, output_path))

        if not jobs:
            messagebox.showinfo("Nothing to do", "No images to convert.")
            return

        # Two things are worth saying before a long trace starts, both framed as
        # help rather than as warnings, and both leaving the choice with the user.
        max_long_edge = None

        # 1. A very large image costs far more to trace than it returns, and an
        #    SVG scales on its own, so offer the cheaper path.
        biggest = max(jobs, key=lambda job: svg_converter.image_pixels(job[0]))
        if svg_converter.is_large_image(biggest[0]):
            try:
                with Image.open(biggest[0]) as probe_img:
                    width, height = probe_img.size
            except Exception:
                width = height = 0
            limit = svg_converter.SUGGESTED_MAX_LONG_EDGE
            if messagebox.askyesno(
                "Large image",
                f"{os.path.basename(biggest[0])} is {width}×{height}, which is a lot "
                "of detail to trace.\n\n"
                "An SVG scales to any size on its own, so tracing it at "
                f"{limit} pixels will look the same while keeping the file much "
                "lighter and the wait much shorter.\n\n"
                "Trace at the smaller size?",
            ):
                max_long_edge = limit

        # 2. Some images simply do not suit the format. Estimating costs about a
        #    second (it traces a miniature), which is worth it to avoid handing
        #    someone a file heavier than the original they started from.
        estimate = svg_converter.estimate_svg_mb(biggest[0], opts, max_long_edge)
        if estimate >= svg_converter.HEAVY_SVG_MB:
            if not messagebox.askyesno(
                "Heads up",
                "This one is packed with detail, so the SVG should come out around "
                f"{estimate:.0f} MB — heavier than the original, and slower to "
                "open than it.\n\n"
                "SVG is at its best with flat artwork, logos and line art. For an "
                "image like this, staying with PNG or JPG usually serves you "
                "better.\n\n"
                "Convert to SVG anyway?",
            ):
                return

        logger = ConversionService()
        errors: list[str] = []
        done_paths: list[str] = []

        def work(report, set_status):
            for index, (src, dst) in enumerate(jobs):
                set_status(f"{os.path.basename(src)}  ({index + 1}/{len(jobs)})")
                try:
                    svg_converter.vectorize(
                        src, dst, opts, status=None, max_long_edge=max_long_edge
                    )
                    done_paths.append(dst)
                    try:
                        logger.log_success("image_to_svg", src, dst)
                    except Exception:
                        pass
                except Exception as exc:
                    errors.append(f"{os.path.basename(src)}: {exc}")
                    try:
                        logger.log_error("image_to_svg", src, str(exc))
                    except Exception:
                        pass
                report(((index + 1) / len(jobs)) * 100.0)

        try:
            run_with_progress_status(self.root, "Converting to SVG", work)
        except Exception as exc:
            messagebox.showerror("Error", f"Error during conversion: {exc}")
            return

        converted = len(done_paths)
        if errors and converted == 0:
            messagebox.showerror("Error", "No images were converted.\n" + "\n".join(errors[:5]))
        elif errors:
            messagebox.showwarning(
                "Partial Success",
                f"Converted {converted}/{len(jobs)} images. Some failed:\n" + "\n".join(errors[:5]),
            )
        else:
            messagebox.showinfo("Success", f"Converted {converted}/{len(jobs)} images successfully!")

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
                # SVG inputs are rendered rather than decoded by Pillow. 2x keeps
                # the result crisp, since a vector has no natural pixel size.
                if input_extension == 'svg':
                    if not svg_converter.svg_render_available():
                        raise RuntimeError(
                            "reading SVG files needs the 'resvg-py' package "
                            "(pip install resvg-py)"
                        )
                    svg_converter.rasterize(file, output_path, output_format, scale=2.0)
                    converted += 1
                    try:
                        logger.log_success("svg_to_image", file, output_path)
                    except Exception:
                        pass
                    continue

                with Image.open(file) as img:
                    fmt = output_format.lower()
                    # Adjust save strategy for very large images to reduce memory spikes
                    try:
                        w, h = img.size
                        px = w * h
                        is_huge = px >= 100_000_000  # ~100 MP threshold
                    except Exception:
                        is_huge = False
                    if fmt in ('jpg', 'jpeg'):
                        # Ensure no alpha channel: flatten onto white background if needed
                        if img.mode in ("RGBA", "LA") or (img.mode == "P" and 'transparency' in img.info):
                            img = img.convert("RGBA")
                            bg = Image.new("RGB", img.size, (255, 255, 255))
                            bg.paste(img, mask=img.split()[3])
                            img = bg
                        else:
                            img = img.convert("RGB")
                        # For huge images, avoid optimize/subsampling=0 to curb RAM usage
                        if is_huge:
                            img.save(output_path, format='JPEG', quality=90)
                        else:
                            img.save(output_path, format='JPEG', quality=100, subsampling=0, optimize=True)
                    else:
                        # For formats supporting alpha, keep original mode
                        if fmt == 'png' and is_huge:
                            # Avoid expensive optimizations on huge PNGs
                            img.save(output_path, format='PNG', compress_level=6, optimize=False)
                        else:
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