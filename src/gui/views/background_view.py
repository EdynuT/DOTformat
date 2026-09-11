"""Background removal view: owns every dialog and the post-processing editor;
all business logic lives in ``services.background_service.BackgroundService``
(reached via ``ctx.background_service``).
"""
from __future__ import annotations

import os
from tkinter import Button, Canvas, Label, Scale, Toplevel, filedialog, messagebox

from PIL import Image, ImageTk

from ..context import AppContext
from ..widgets.progress import run_with_progress_status
from ...services.job_runner import OperationCancelled
from ...utils.console_log import log_error
from ...utils.user_settings import get_setting, set_setting


def remove_background_action(ctx: AppContext) -> None:
    try:
        _remove_background_flow(ctx)
    except Exception as e:
        ctx.conversion_service.log_error("remove_background", None, str(e), username=ctx.current_user)
        log_error(f"Background removal failed: {e}")


def _remove_background_flow(ctx: AppContext) -> None:
    service = ctx.background_service
    filetypes = [
        ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"),
        ("All Files", "*.*"),
    ]
    input_path = filedialog.askopenfilename(
        title="Select image", initialdir=(get_setting("last_dir_image") or ""), filetypes=filetypes
    )
    if not input_path:
        return
    set_setting("last_dir_image", os.path.dirname(input_path))

    # Preflight: check for heavy dependencies before opening any progress UI, so
    # systems/executables without them bundled (e.g. no-console builds) fail
    # fast with a clear message instead of a long "Loading…" wait.
    missing = service.check_dependencies()
    if missing:
        messagebox.showerror(
            "Background removal unavailable",
            (
                "This feature needs extra AI libraries that aren't bundled in the portable build.\n\n"
                "Required packages:\n  - " + "\n  - ".join(missing) + "\n\n"
                "To use background removal, run DOTformat from source and install them:\n"
                "python -m pip install " + " ".join(missing)
            ),
        )
        return

    def work(report, set_status, cancel_event):
        return service.remove_background(input_path, cancel_event, report, set_status)

    try:
        output_image = run_with_progress_status(ctx.root, "Removing background…", work)
    except OperationCancelled:
        messagebox.showinfo("Cancelled", "Background removal was cancelled.")
        return
    except Exception as e:
        messagebox.showerror("Error", f"Failed to remove background: {e}")
        return

    _open_post_processing_editor(ctx, input_path, output_image)


def _open_post_processing_editor(ctx: AppContext, input_path: str, output_image: Image.Image) -> None:
    service = ctx.background_service
    default_output = service.default_output_path(input_path)

    win = Toplevel(ctx.root)
    win.title("Background Removed - Post Processing")
    win.configure(bg="#1C1C1C")
    win.grab_set()

    undo_stack: list[Image.Image] = []

    canvas = Canvas(win, width=400, height=400, bg="#1C1C1C", highlightthickness=0)
    canvas.grid(row=0, column=1, rowspan=6, padx=10, pady=10)

    def update_canvas_image(img: Image.Image) -> None:
        img_disp = img.copy()
        img_disp.thumbnail((400, 400))
        tk_img = ImageTk.PhotoImage(img_disp)
        canvas.image = tk_img
        canvas.delete("all")
        canvas.create_image(200, 200, image=tk_img)

    update_canvas_image(output_image)

    def save_state() -> None:
        undo_stack.append(output_image.copy())
        if len(undo_stack) > 100:
            undo_stack.pop(0)

    def undo_action() -> None:
        nonlocal output_image
        if undo_stack:
            output_image = undo_stack.pop()
            update_canvas_image(output_image)

    def apply_edited(new_image: Image.Image) -> None:
        nonlocal output_image
        output_image = new_image
        update_canvas_image(output_image)

    def enable_manual_eraser() -> None:
        _open_manual_eraser(ctx, win, output_image, on_apply=apply_edited)

    def apply_clean_mask() -> None:
        save_state()
        apply_edited(service.apply_clean_mask(output_image))

    def apply_fill_holes() -> None:
        save_state()
        apply_edited(service.apply_fill_holes(output_image))

    def apply_smooth_edges() -> None:
        save_state()
        apply_edited(service.apply_smooth_edges(output_image))

    def save_and_exit() -> None:
        service.save(output_image, default_output, input_path, username=ctx.current_user)
        messagebox.showinfo("Saved", f"Image saved at: {default_output}")
        win.destroy()

    def save_without_editing() -> None:
        service.save(output_image, default_output, input_path, username=ctx.current_user)
        win.destroy()

    # --- Layout: Controls ---
    Button(win, text="⟲", command=undo_action).grid(row=2, column=0, padx=5, pady=5)
    Button(win, text="Manual Eraser", command=enable_manual_eraser).grid(row=3, column=0, padx=5, pady=5)
    Button(win, text="Clean Mask", command=apply_clean_mask).grid(row=4, column=0, padx=5, pady=5)
    Button(win, text="Fill Holes", command=apply_fill_holes).grid(row=5, column=0, padx=5, pady=5)
    Button(win, text="Smooth Edges", command=apply_smooth_edges).grid(row=6, column=0, padx=5, pady=5)
    Button(win, text="Save and Exit", command=save_and_exit).grid(row=7, column=1, padx=5, pady=5, sticky="e")
    Button(win, text="Exit Without Editing", command=save_without_editing).grid(row=7, column=1, padx=5, pady=5, sticky="w")


def _open_manual_eraser(ctx: AppContext, parent_win, initial_image: Image.Image, on_apply) -> None:
    """Zoom (centered on cursor), pan (right-drag), and a circular eraser brush."""
    service = ctx.background_service
    manual_win = Toplevel(parent_win)
    manual_win.title("Manual Eraser Mode")
    manual_win.configure(bg="#1C1C1C")
    manual_win.grab_set()

    zoom_factor = [1.0]
    brush_radius = [10]
    offset = [0, 0]
    drag_start = [0, 0]
    undo_stack_manual: list[Image.Image] = []

    edited_image = initial_image.copy()

    canvas_manual = Canvas(manual_win, width=600, height=600, bg="#1C1C1C", highlightthickness=0)
    canvas_manual.grid(row=0, column=1, rowspan=6, padx=10, pady=10)

    def update_canvas_image_manual() -> None:
        img_disp = edited_image.copy()
        w, h = img_disp.size
        new_size = (int(w * zoom_factor[0]), int(h * zoom_factor[0]))
        img_disp = img_disp.resize(new_size, Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img_disp)
        canvas_manual.image = tk_img
        canvas_manual.delete("all")
        canvas_manual.create_image(offset[0], offset[1], anchor="nw", image=tk_img)

    def on_brush_size_change(val) -> None:
        brush_radius[0] = int(val)

    def save_state_manual() -> None:
        undo_stack_manual.append(edited_image.copy())
        if len(undo_stack_manual) > 20:
            undo_stack_manual.pop(0)

    def undo_action_manual() -> None:
        nonlocal edited_image
        if undo_stack_manual:
            edited_image = undo_stack_manual.pop()
            update_canvas_image_manual()

    def canvas_to_image_coords_manual(x, y) -> tuple[int, int]:
        img_x = int((x - offset[0]) / zoom_factor[0])
        img_y = int((y - offset[1]) / zoom_factor[0])
        return img_x, img_y

    def paint_manual(event) -> None:
        nonlocal edited_image
        img_x, img_y = canvas_to_image_coords_manual(event.x, event.y)
        edited_image = service.erase_circle(edited_image, (img_x, img_y), brush_radius[0])
        update_canvas_image_manual()

    def show_eraser_manual(event) -> None:
        # brush_radius is in image pixels, fixed regardless of zoom -- only the
        # on-screen preview circle should grow/shrink with zoom to still match
        # where the brush will actually land.
        canvas_manual.delete("eraser_preview")
        x, y = event.x, event.y
        r = brush_radius[0] * zoom_factor[0]
        canvas_manual.create_oval(x - r, y - r, x + r, y + r, outline="red", fill="", width=2, tags="eraser_preview")

    def on_mouse_wheel(event) -> None:
        # Windows/macOS deliver <MouseWheel> with a signed event.delta; X11
        # (Linux) has no such event and instead sends scroll as button clicks,
        # <Button-4> (up) / <Button-5> (down), with event.delta always 0.
        if event.num == 5 or event.delta < 0:
            zoom_in = False
        elif event.num == 4 or event.delta > 0:
            zoom_in = True
        else:
            return

        mouse_x, mouse_y = event.x, event.y
        old_zoom = zoom_factor[0]
        if zoom_in and zoom_factor[0] < 5.0:
            zoom_factor[0] *= 1.1
        elif not zoom_in and zoom_factor[0] > 1.0:
            zoom_factor[0] /= 1.1
        scale = zoom_factor[0] / old_zoom
        offset[0] = int(mouse_x - scale * (mouse_x - offset[0]))
        offset[1] = int(mouse_y - scale * (mouse_y - offset[1]))
        update_canvas_image_manual()

    def start_drag(event) -> None:
        drag_start[0] = event.x - offset[0]
        drag_start[1] = event.y - offset[1]

    def drag(event) -> None:
        offset[0] = event.x - drag_start[0]
        offset[1] = event.y - drag_start[1]
        update_canvas_image_manual()

    def exit_manual_eraser() -> None:
        result = messagebox.askyesnocancel(
            "Exit Manual Eraser",
            "Save changes before exiting?\nYes: Save and Exit\nNo: Exit Without Saving\nCancel: Stay",
            parent=manual_win,
        )
        if result is None:
            return
        if result:
            on_apply(edited_image.copy())
        manual_win.destroy()

    Button(manual_win, text="⟲", command=undo_action_manual).grid(row=0, column=0, padx=10, pady=10, sticky="nw")

    Label(manual_win, text="Brush Size", bg="#1C1C1C", fg="white").grid(
        row=1, column=0, sticky="n", padx=(10, 0), pady=(10, 0)
    )
    Label(manual_win, text="100", bg="#1C1C1C", fg="white").grid(
        row=2, column=0, sticky="n", padx=(25, 0), pady=(0, 0)
    )
    brush_scale_manual = Scale(
        manual_win, from_=100, to=1, orient="vertical", showvalue=0,
        command=on_brush_size_change, length=250,
    )
    brush_scale_manual.set(brush_radius[0])
    brush_scale_manual.grid(row=3, column=0, padx=(30, 0), pady=(0, 0), sticky="n")
    Label(manual_win, text="1", bg="#1C1C1C", fg="white").grid(
        row=4, column=0, sticky="n", padx=(25, 0), pady=(0, 0)
    )

    Button(manual_win, text="Exit Manual Eraser", command=exit_manual_eraser).grid(
        row=5, column=1, padx=10, pady=10, sticky="se"
    )

    def start_draw_manual(event) -> None:
        save_state_manual()
        paint_manual(event)

    canvas_manual.bind("<B1-Motion>", paint_manual)
    canvas_manual.bind("<ButtonPress-1>", start_draw_manual)
    canvas_manual.bind("<Motion>", show_eraser_manual)
    canvas_manual.bind("<MouseWheel>", on_mouse_wheel)
    canvas_manual.bind("<Button-4>", on_mouse_wheel)
    canvas_manual.bind("<Button-5>", on_mouse_wheel)
    canvas_manual.bind("<ButtonPress-3>", start_drag)
    canvas_manual.bind("<B3-Motion>", drag)

    update_canvas_image_manual()


__all__ = ["remove_background_action"]
