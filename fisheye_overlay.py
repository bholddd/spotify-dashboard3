"""
fisheye_overlay.py  —  CRT vignette overlay, no screenshots, no Toplevel.

How it works
------------
A tkinter Canvas is placed over the entire parent window using place().
It renders a pre-built RGBA image: dark vignette from edges + rounded corners
+ scanlines. The centre of the image is fully transparent so content shows.

On Windows a plain Canvas intercepts mouse events. We fix this by binding
every relevant event on the canvas and re-dispatching it to whichever widget
sits underneath using winfo_containing().
"""

import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageTk

# ── tunables ──────────────────────────────────────────────────────────────────
CORNER_R   = 26      # rounded corner radius in pixels
EDGE_FADE  = 44      # vignette depth from each edge in pixels
VIGNETTE_A = 160     # max vignette opacity (0–255); lower = subtler
REFRESH_MS = 300     # ms between redraws (only matters on window resize)
# ─────────────────────────────────────────────────────────────────────────────


def _build_overlay(w: int, h: int) -> Image.Image:
    """
    Build an RGBA overlay image.
    Centre pixels are (0,0,0,0) — fully transparent.
    Edge/corner pixels are (0,0,0,alpha) — dark.
    """
    # ── vignette alpha (dark at edges, transparent in centre) ────────────────
    vig = Image.new("L", (w, h), 0)
    vd  = ImageDraw.Draw(vig)
    for i in range(EDGE_FADE):
        t = i / EDGE_FADE          # 0 at edge → 1 at inner boundary
        a = int(VIGNETTE_A * (1.0 - t) ** 2.0)
        vd.rectangle([i, i, w - 1 - i, h - 1 - i], outline=a)
    vig = vig.filter(ImageFilter.GaussianBlur(radius=EDGE_FADE * 0.4))

    # ── rounded corner alpha (corners fully dark, inside transparent) ─────────
    corner = Image.new("L", (w, h), 255)          # start fully opaque
    ImageDraw.Draw(corner).rounded_rectangle(
        [0, 0, w - 1, h - 1], radius=CORNER_R, fill=0
    )
    corner = corner.filter(ImageFilter.GaussianBlur(radius=5))

    # ── combine: take the maximum of vignette and corner alpha ───────────────
    combined = Image.new("L", (w, h), 0)
    for y in range(h):
        for x in range(w):
            combined.putpixel(
                (x, y),
                min(255, max(vig.getpixel((x, y)), corner.getpixel((x, y))))
            )

    # ── scanlines (every 3rd row gets a faint dark stripe) ───────────────────
    scan_layer = Image.new("L", (w, h), 0)
    sdraw = ImageDraw.Draw(scan_layer)
    for y in range(0, h, 3):
        sdraw.line([(0, y), (w - 1, y)], fill=20)

    # Merge scanlines additively into combined, capped at 255
    for y in range(0, h, 3):
        for x in range(w):
            old = combined.getpixel((x, y))
            combined.putpixel((x, y), min(255, old + 20))

    # ── assemble RGBA ─────────────────────────────────────────────────────────
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.putalpha(combined)
    return out


def _build_overlay_fast(w: int, h: int) -> Image.Image:
    """Faster version avoiding per-pixel Python loops."""
    import numpy as np

    alpha = np.zeros((h, w), dtype=np.float32)

    # vignette
    for i in range(EDGE_FADE):
        t = i / EDGE_FADE
        a = VIGNETTE_A * (1.0 - t) ** 2.0
        alpha[i, :]      = np.maximum(alpha[i, :],      a)
        alpha[h-1-i, :]  = np.maximum(alpha[h-1-i, :],  a)
        alpha[:, i]      = np.maximum(alpha[:, i],      a)
        alpha[:, w-1-i]  = np.maximum(alpha[:, w-1-i],  a)

    alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    vig_img = Image.fromarray(alpha, mode="L")
    vig_img = vig_img.filter(ImageFilter.GaussianBlur(radius=EDGE_FADE * 0.4))
    alpha   = np.array(vig_img, dtype=np.float32)

    # rounded corners via PIL mask
    corner = Image.new("L", (w, h), 255)
    ImageDraw.Draw(corner).rounded_rectangle(
        [0, 0, w - 1, h - 1], radius=CORNER_R, fill=0
    )
    corner = corner.filter(ImageFilter.GaussianBlur(radius=5))
    c_arr  = np.array(corner, dtype=np.float32)

    combined = np.maximum(alpha, c_arr)

    # scanlines
    combined[::3, :] = np.minimum(combined[::3, :] + 20, 255)

    final = np.clip(combined, 0, 255).astype(np.uint8)

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 3] = final          # black colour, variable alpha
    return Image.fromarray(rgba, "RGBA")


# pick fastest available implementation
try:
    import numpy as _np
    _build = _build_overlay_fast
except ImportError:
    _build = _build_overlay


class FisheyeOverlay:
    """
    CRT vignette + rounded corners rendered as a canvas inside the parent.

    The canvas sits on top of all widgets using place(relwidth=1, relheight=1).
    Mouse events that hit the canvas are caught and re-dispatched to the real
    widget underneath so clicking, dragging, and scrolling all work normally.
    """

    _FORWARD = (
        "<Button-1>", "<ButtonRelease-1>", "<B1-Motion>",
        "<Button-2>", "<ButtonRelease-2>",
        "<Button-3>", "<ButtonRelease-3>",
        "<MouseWheel>", "<Double-Button-1>",
        "<Enter>", "<Leave>",
    )

    def __init__(self, parent: tk.Tk, enabled: bool = True):
        self._parent  = parent
        self._enabled = enabled
        self._job     = None
        self._photo   = None
        self._last_wh = (0, 0)

        self._canvas = tk.Canvas(
            parent,
            highlightthickness=0,
            borderwidth=0,
            bg=parent.cget("bg"),   # match window bg so it doesn't flash
            cursor="",
        )

        if enabled:
            self._show()
        # Forward all mouse events through the canvas to widgets below
        self._bind_passthrough()

    # ── public ────────────────────────────────────────────────────────────────

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
            if self._job:
                self._parent.after_cancel(self._job)
                self._job = None
            self._canvas.place_forget()
        else:
            self._show()

    def destroy(self):
        if self._job:
            self._parent.after_cancel(self._job)
            self._job = None
        try:
            self._canvas.destroy()
        except tk.TclError:
            pass

    # ── internal ──────────────────────────────────────────────────────────────

    def _show(self):
        self._canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self._canvas.lift()
        self._schedule()

    def _bind_passthrough(self):
        """
        Re-dispatch every mouse event to the actual widget under the cursor,
        skipping the canvas itself.  This makes the overlay invisible to
        interaction — clicks/drags/scroll all reach the intended widget.
        """
        def _forward(event):
            # Find the widget directly under the pointer (excluding this canvas)
            target = event.widget.winfo_containing(event.x_root, event.y_root)
            if target and target is not self._canvas:
                try:
                    target.event_generate(event.type.name if hasattr(event.type, 'name') else str(event.type),
                                          x=event.x, y=event.y,
                                          rootx=event.x_root, rooty=event.y_root,
                                          delta=getattr(event, 'delta', 0),
                                          state=event.state)
                except Exception:
                    pass

        def _forward_scroll(event):
            target = event.widget.winfo_containing(event.x_root, event.y_root)
            if target and target is not self._canvas:
                try:
                    target.event_generate("<MouseWheel>",
                                          delta=event.delta,
                                          x=event.x, y=event.y,
                                          rootx=event.x_root, rooty=event.y_root)
                except Exception:
                    pass

        for seq in self._FORWARD:
            if "MouseWheel" in seq:
                self._canvas.bind(seq, _forward_scroll, add=False)
            else:
                self._canvas.bind(seq, _forward, add=False)

    def _refresh(self):
        if not self._enabled:
            return

        self._parent.update_idletasks()
        w = self._parent.winfo_width()
        h = self._parent.winfo_height()
        if w < 10 or h < 10:
            return

        if (w, h) != self._last_wh:
            self._last_wh = (w, h)
            img           = _build(w, h)
            self._photo   = ImageTk.PhotoImage(img)
            self._canvas.config(width=w, height=h)

        self._canvas.delete("all")
        if self._photo:
            self._canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)
        self._canvas.lift()

    def _schedule(self):
        self._refresh()
        self._job = self._parent.after(REFRESH_MS, self._schedule)