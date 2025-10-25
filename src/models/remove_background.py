"""Background removal tool with optional heavy dependencies (rembg, numpy, cv2).

This module defers importing heavy libraries until the user invokes the
background removal action, so the rest of the GUI can load even if they
are not installed. Errors are reported with friendly dialogs.
"""

from tkinter import filedialog, messagebox, Toplevel, Button, Scale, Canvas, Label
from src.utils.user_settings import get_setting, set_setting
from PIL import Image, ImageFilter, ImageTk
import os
from src.services.conversion_service import ConversionService


def clean_mask(image: Image.Image) -> Image.Image:
    """Apply a median filter to remove small noise in the alpha/mask."""
    return image.filter(ImageFilter.MedianFilter(size=3))


def fill_small_holes(pil_image: Image.Image) -> Image.Image:
    """Fill small holes in alpha channel (best effort if deps present)."""
    try:
        import numpy as np  # type: ignore
        import cv2  # type: ignore
    except Exception:
        return pil_image
    try:
        img = np.array(pil_image)
        if img.shape[2] == 4:
            alpha = img[:, :, 3]
            mask = cv2.threshold(alpha, 0, 255, cv2.THRESH_BINARY)[1]
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            img[:, :, 3] = mask
            return Image.fromarray(img)
    except Exception:
        return pil_image
    return pil_image


def smooth_edges(pil_image: Image.Image) -> Image.Image:
    """Slight Gaussian blur on alpha to soften edges."""
    img = pil_image.convert("RGBA")
    r, g, b, a = img.split()
    a = a.filter(ImageFilter.GaussianBlur(radius=1))
    return Image.merge("RGBA", (r, g, b, a))


def remove_background():  # noqa: C901 (complexity acceptable for GUI handler)
    """Open file dialog, remove background with rembg (if installed), allow post-processing."""
    filetypes = [
        ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"),
        ("All Files", "*.*")
    ]
    try:
        input_path = filedialog.askopenfilename(title="Select image", initialdir=(get_setting("last_dir_image") or ""), filetypes=filetypes)
    except Exception as e:
        # Log GUI selection error
        try:
            ConversionService().log_error("remove_background", None, f"Open dialog failed: {e}")
        except Exception:
            pass
        return False, str(e)
    if not input_path:
        # User cancelled the dialog; do nothing.
        return

    if input_path:
        set_setting("last_dir_image", os.path.dirname(input_path))
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    base, _ = os.path.splitext(os.path.basename(input_path))
    default_output = os.path.join(desktop, f"{base}_nobg.png")

    # Lazy heavy imports
    try:
        import numpy as np  # type: ignore
    except Exception:
        messagebox.showerror(
            "Missing dependency",
            "Missing 'numpy'. Install with:\n  python -m pip install numpy"
        )
        try:
            ConversionService().log_error("remove_background", input_path, "Missing dependency: numpy")
        except Exception:
            pass
        return
    try:
        import cv2  # type: ignore
    except Exception:
        messagebox.showerror(
            "Missing dependency",
            "Missing 'opencv-python-headless'. Install with:\n  python -m pip install opencv-python-headless"
        )
        try:
            ConversionService().log_error("remove_background", input_path, "Missing dependency: opencv-python-headless")
        except Exception:
            pass
        return
    try:
        from rembg import remove  # type: ignore
    except Exception:
        messagebox.showerror(
            "Missing dependency",
            "Missing 'rembg'. Optional feature. Install with:\n  python -m pip install rembg"
        )
        try:
            ConversionService().log_error("remove_background", input_path, "Missing dependency: rembg")
        except Exception:
            pass
        return

    # Show a determinate progress window while removing background (worker thread does inference)
    from tkinter import Toplevel, ttk
    import threading
    import tkinter as tk
    prog = Toplevel()
    prog.title("Removing background...")
    prog.geometry("320x110")
    prog.resizable(False, False)
    prog.grab_set()

    msg = tk.StringVar(value="Loading image…")
    ttk.Label(prog, textvariable=msg).pack(pady=(10, 6))

    pvar = tk.DoubleVar(value=0.0)
    bar = ttk.Progressbar(prog, mode='determinate', maximum=100, variable=pvar, length=260)
    bar.pack(pady=6)

    stop_nudge = threading.Event()

    def tick():
        # Gentle progress while the model runs; capped at 90%
        try:
            if not stop_nudge.is_set():
                cur = float(pvar.get())
                if cur < 90.0:
                    pvar.set(min(90.0, cur + 0.6))
                prog.after(200, tick)
        except Exception:
            pass

    # Start gentle nudger later, after we switch to model phase
    prog.after(300, tick)

    result = {"img": None, "err": None}

    def _set_msg(text: str):
        try:
            prog.after(0, lambda: msg.set(text))
        except Exception:
            pass

    def _set_progress(val: float):
        try:
            prog.after(0, lambda: pvar.set(max(0.0, min(100.0, float(val)))))
        except Exception:
            pass

    def _worker():
        try:
            _set_msg("Loading image…")
            _set_progress(5)
            input_image = Image.open(input_path)

            _set_msg("Applying AI model…")
            _set_progress(10)
            img = remove(input_image)

            _set_msg("Finalizing…")
            _set_progress(95)
            result["img"] = img
        except Exception as e:  # pragma: no cover (runtime UX path)
            result["err"] = e
        finally:
            try:
                stop_nudge.set()
                prog.after(0, lambda: pvar.set(100.0))
                prog.after(100, prog.destroy)
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()
    # Block until the progress window closes
    prog.wait_window()
    if result["err"] is not None:
        try:
            ConversionService().log_error("remove_background", input_path, f"Failed to remove background: {result['err']}")
        except Exception:
            pass
        return "Error, Failed to remove background", str(result["err"]) 
    output_image = result["img"]

    # --- Post-processing Window ---
    win = Toplevel()
    win.title("Background Removed - Post Processing")
    win.configure(bg="#1C1C1C")
    win.grab_set()
    # Variables for brush and undo stack
    brush_radius = 10  # Initial brush size
    undo_stack = []    # Stack to store previous image states for undo
    manual_eraser = {'active': False}  # Manual eraser mode flag

    # Canvas for image display and drawing
    canvas = Canvas(win, width=400, height=400, bg="#1C1C1C", highlightthickness=0)
    canvas.grid(row=0, column=1, rowspan=6, padx=10, pady=10)

    def update_canvas_image(img):
        """
        Updates the canvas with the current image and keeps a reference to avoid garbage collection.
        """
        img_disp = img.copy()
        img_disp.thumbnail((400, 400))
        tk_img = ImageTk.PhotoImage(img_disp)
        canvas.image = tk_img
        canvas.delete("all")
        canvas.create_image(200, 200, image=tk_img)

    # Initial display
    update_canvas_image(output_image)

    def save_state():
        """
        Saves the current image state to the undo stack.
        """
        undo_stack.append(output_image.copy())
        if len(undo_stack) > 100:  # Limit history to 100 steps
            undo_stack.pop(0)

    def undo_action():
        """
        Restores the previous image state from the undo stack.
        """
        nonlocal output_image
        if undo_stack:
            output_image = undo_stack.pop()
            update_canvas_image(output_image)

    def on_brush_size_change(val):
        """
        Updates the brush radius when the scale is moved.
        """
        nonlocal brush_radius
        brush_radius = int(val)

    # --- Manual Eraser Mode ---
    def enable_manual_eraser():
        """
        Opens a new window for manual erasing with brush size, undo, zoom (centered on cursor),
        and panning (drag with right mouse button).
        """
        manual_win = Toplevel(win)
        manual_win.title("Manual Eraser Mode")
        manual_win.configure(bg="#1C1C1C")
        manual_win.grab_set()

        # Variables for zoom, brush, pan offset, and undo stack
        zoom_factor = [1.0]  # Mutable for nested functions
        brush_radius = [10]
        offset = [0, 0]      # Pan offset (x, y)
        drag_start = [0, 0]  # Mouse position at start of drag
        undo_stack_manual = []

        # Copy the current image for editing
        edited_image = output_image.copy()

        # Canvas for editing
        canvas_manual = Canvas(manual_win, width=600, height=600, bg="#1C1C1C", highlightthickness=0)
        canvas_manual.grid(row=0, column=1, rowspan=6, padx=10, pady=10)

        def update_canvas_image_manual():
            """
            Draws the image on the canvas at the current zoom level and offset.
            """
            img_disp = edited_image.copy()
            w, h = img_disp.size
            new_size = (int(w * zoom_factor[0]), int(h * zoom_factor[0]))
            img_disp = img_disp.resize(new_size, Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(img_disp)
            canvas_manual.image = tk_img
            canvas_manual.delete("all")
            # Draw image at current offset
            canvas_manual.create_image(offset[0], offset[1], anchor="nw", image=tk_img)

        def on_brush_size_change(val):
            brush_radius[0] = int(val)

        def save_state_manual():
            undo_stack_manual.append(edited_image.copy())
            if len(undo_stack_manual) > 20:
                undo_stack_manual.pop(0)

        def undo_action_manual():
            nonlocal edited_image
            if undo_stack_manual:
                edited_image = undo_stack_manual.pop()
                update_canvas_image_manual()

        def canvas_to_image_coords_manual(x, y):
            """
            Converts canvas coordinates to image coordinates, considering zoom and offset.
            """
            img_x = int((x - offset[0]) / zoom_factor[0])
            img_y = int((y - offset[1]) / zoom_factor[0])
            return img_x, img_y

        def paint_manual(event):
            """
            Erases (makes transparent) a circular area under the cursor.
            """
            nonlocal edited_image
            img_x, img_y = canvas_to_image_coords_manual(event.x, event.y)
            img_np = np.array(edited_image)
            if img_np.shape[2] == 4:
                alpha = img_np[:, :, 3].copy()
                cv2.circle(alpha, (img_x, img_y), brush_radius[0], 0, -1)
                img_np[:, :, 3] = alpha
                edited_image = Image.fromarray(img_np)
                update_canvas_image_manual()

        def show_eraser_manual(event):
            """
            Draws the brush preview (red circle) at the cursor position, considering zoom and offset.
            """
            canvas_manual.delete("eraser_preview")
            x, y = event.x, event.y
            r = brush_radius[0]
            canvas_manual.create_oval(x - r, y - r, x + r, y + r, outline="red", fill="", width=2, tags="eraser_preview")

        def on_mouse_wheel(event):
            """
            Zooms in/out centered on the mouse cursor.
            """
            mouse_x, mouse_y = event.x, event.y
            old_zoom = zoom_factor[0]
            if event.delta > 0 and zoom_factor[0] < 5.0:
                zoom_factor[0] *= 1.1
            elif event.delta < 0 and zoom_factor[0] > 1.0:
                zoom_factor[0] /= 1.1
            # Adjust offset so the point under the cursor stays under the cursor
            scale = zoom_factor[0] / old_zoom
            offset[0] = int(mouse_x - scale * (mouse_x - offset[0]))
            offset[1] = int(mouse_y - scale * (mouse_y - offset[1]))
            update_canvas_image_manual()

        # --- Dragging with right mouse button ---
        def start_drag(event):
            drag_start[0] = event.x - offset[0]
            drag_start[1] = event.y - offset[1]

        def drag(event):
            offset[0] = event.x - drag_start[0]
            offset[1] = event.y - drag_start[1]
            update_canvas_image_manual()

        def exit_manual_eraser():
            # Ask user if wants to save changes
            result = messagebox.askyesnocancel(
                "Exit Manual Eraser",
                "Save changes before exiting?\nYes: Save and Exit\nNo: Exit Without Saving\nCancel: Stay",
                parent=manual_win
            )
            if result is None:
                return  # Cancelled
            elif result:
                # Save changes to main image
                nonlocal output_image
                output_image = edited_image.copy()
                update_canvas_image(output_image)
                manual_win.destroy()
            else:
                manual_win.destroy()

        # Undo button (top-left)
        btn_undo_manual = Button(manual_win, text="⟲", command=undo_action_manual)
        btn_undo_manual.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

        # Brush size title above the scale
        lbl_brush_title = Label(manual_win, text="Brush Size", bg="#1C1C1C", fg="white")
        lbl_brush_title.grid(row=1, column=0, sticky="n", padx=(10,0), pady=(10,0))

        # Number 100 (top, left of scale)
        lbl_100 = Label(manual_win, text="100", bg="#1C1C1C", fg="white")
        lbl_100.grid(row=2, column=0, sticky="n", padx=(25,0), pady=(0,0))

        # Brush size scale (vertical, left, centered)
        brush_scale_manual = Scale(
            manual_win, from_=100, to=1, orient="vertical", showvalue=0,
            command=on_brush_size_change, length=250
        )
        brush_scale_manual.set(brush_radius[0])
        brush_scale_manual.grid(row=3, column=0, padx=(30,0), pady=(0,0), sticky="n")

        # Number 1 (bottom, left of scale)
        lbl_1 = Label(manual_win, text="1", bg="#1C1C1C", fg="white")
        lbl_1.grid(row=4, column=0, sticky="n", padx=(25,0), pady=(0,0))

        # Canvas for editing (right side, spanning most rows)
        canvas_manual = Canvas(manual_win, width=600, height=600, bg="#1C1C1C", highlightthickness=0)
        canvas_manual.grid(row=0, column=1, rowspan=6, padx=10, pady=10)

        # Exit button (bottom-right)
        btn_exit_manual = Button(manual_win, text="Exit Manual Eraser", command=exit_manual_eraser)
        btn_exit_manual.grid(row=5, column=1, padx=10, pady=10, sticky="se")
        
        # Canvas bindings
        def start_draw_manual(event):
            save_state_manual()
            paint_manual(event)

        canvas_manual.bind("<B1-Motion>", paint_manual)
        canvas_manual.bind("<ButtonPress-1>", start_draw_manual)
        canvas_manual.bind("<Motion>", show_eraser_manual)
        canvas_manual.bind("<MouseWheel>", on_mouse_wheel)
        canvas_manual.bind("<ButtonPress-3>", start_drag)
        canvas_manual.bind("<B3-Motion>", drag)

        update_canvas_image_manual()

    # --- Post-processing Actions ---
    def apply_clean_mask():
        """
        Applies median filter to clean mask.
        """
        save_state()
        nonlocal output_image
        output_image = clean_mask(output_image)
        update_canvas_image(output_image)

    def apply_fill_holes():
        """Fills small holes in alpha (best-effort if dependencies present)."""
        save_state()
        nonlocal output_image
        output_image = fill_small_holes(output_image)
        update_canvas_image(output_image)
    def apply_smooth_edges():
        """
        Smooths the alpha channel edges.
        """
        save_state()
        nonlocal output_image
        output_image = smooth_edges(output_image)
        update_canvas_image(output_image)

    def save_and_exit():
        """
        Saves the processed image and closes the window.
        """
        output_image.save(default_output)
        messagebox.showinfo("Saved", f"Image saved at: {default_output}")
        try:
            ConversionService().log_success("remove_background", input_path, default_output)
        except Exception:
            pass
        win.destroy()

    def save_without_editing():
        """
        Saves the current image without further edits and closes the window.
        """
        output_image.save(default_output)
        try:
            ConversionService().log_success("remove_background", input_path, default_output)
        except Exception:
            pass
        win.destroy()

    # --- Layout: Controls ---
    # Undo button
    btn_undo = Button(win, text="⟲", command=undo_action)
    btn_undo.grid(row=2, column=0, padx=5, pady=5)

    # Manual eraser button
    btn_manual = Button(win, text="Manual Eraser", command=enable_manual_eraser)
    btn_manual.grid(row=3, column=0, padx=5, pady=5)

    # Post-processing buttons
    btn_clean = Button(win, text="Clean Mask", command=apply_clean_mask)
    btn_clean.grid(row=4, column=0, padx=5, pady=5)

    btn_fill = Button(win, text="Fill Holes", command=apply_fill_holes)
    btn_fill.grid(row=5, column=0, padx=5, pady=5)
    btn_smooth = Button(win, text="Smooth Edges", command=apply_smooth_edges)
    btn_smooth.grid(row=6, column=0, padx=5, pady=5)
    # Save and exit buttons
    btn_exit = Button(win, text="Save and Exit", command=save_and_exit)
    btn_exit.grid(row=7, column=1, padx=5, pady=5, sticky="e")
    btn_exit_no_changes = Button(win, text="Exit Without Editing", command=save_without_editing)
    btn_exit_no_changes.grid(row=7, column=1, padx=5, pady=5, sticky="w")
