"""
fisheye_overlay.py  —  CRT vignette + fisheye bulge overlay.
No screenshots, no Toplevel.

How it works
------------
A tkinter Canvas is placed over the entire parent window using place().
It renders a pre-built RGBA image containing:

  1. Dark vignette from edges + rounded corners  (existing)
  2. Barrel-distorted scanlines                  (NEW — key fisheye cue)
  3. Lens glare highlight                        (NEW — reinforces dome shape)

Barrel-distorting the scanlines is the core trick: straight horizontal
stripes look flat, but curved ones fool the eye into perceiving a convex
CRT dome even though the underlying widget pixels are never moved.

On Windows a plain Canvas intercepts mouse events. We fix this by binding
every relevant event on the canvas and re-dispatching it to whichever widget
sits underneath using winfo_containing().
"""

import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageTk

# ── tunables ──────────────────────────────────────────────────────────────────
CORNER_R    = 26     # rounded corner radius in pixels
EDGE_FADE   = 44     # vignette depth from each edge in pixels
VIGNETTE_A  = 160    # max vignette opacity (0–255); lower = subtler

BARREL_K    = 0.18   # barrel distortion strength for scanlines (0 = flat, 0.3 = strong bulge)
SCAN_STEP   = 3      # pixels between scanlines
SCAN_ALPHA  = 22     # scanline darkness (0–255)

GLARE_A     = 18     # peak opacity of the lens-glare highlight (keep subtle, 10–30)
GLARE_POS   = 0.28   # vertical centre of glare as fraction of height (0 = top)

REFRESH_MS  = 300    # ms between redraws (only matters on window resize)
# ─────────────────────────────────────────────────────────────────────────────


def _build_overlay_fast(w: int, h: int) -> Image.Image:
    """
    Build an RGBA overlay image using numpy for speed.

    Alpha channel encodes darkening (black pixels, variable alpha).
    An additive white layer encodes the lens glare brightening.
    """
    import numpy as np

    # ── 1. Vignette ───────────────────────────────────────────────────────────
    alpha = np.zeros((h, w), dtype=np.float32)
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

    # ── 2. Rounded corners ────────────────────────────────────────────────────
    corner = Image.new("L", (w, h), 255)
    ImageDraw.Draw(corner).rounded_rectangle(
        [0, 0, w - 1, h - 1], radius=CORNER_R, fill=0
    )
    corner = corner.filter(ImageFilter.GaussianBlur(radius=5))
    c_arr  = np.array(corner, dtype=np.float32)

    combined = np.maximum(alpha, c_arr)

    # ── 3. Barrel-distorted scanlines ─────────────────────────────────────────
    #
    # For every pixel (x, y) we compute where it would land after barrel
    # distortion and check whether that *distorted* y coordinate falls on a
    # scanline.  The result: scanlines that bow outward in the centre, giving
    # the strong visual cue of a convex CRT screen.
    #
    cx = w / 2.0
    cy = h / 2.0

    # Build coordinate grids (float32 for speed)
    xx = np.tile(np.arange(w, dtype=np.float32), (h, 1))          # (h, w)
    yy = np.tile(np.arange(h, dtype=np.float32).reshape(-1, 1), (1, w))

    # Normalise to [-1, 1]
    xn = (xx - cx) / cx
    yn = (yy - cy) / cy
    r2 = xn * xn + yn * yn

    # Barrel distortion: push outward from centre
    yn_d = yn * (1.0 + BARREL_K * r2)

    # Map back to pixel space
    yd_px = yn_d * cy + cy                                          # (h, w)

    # A pixel is "on a scanline" if its distorted y is in the dark stripe band
    on_scan = ((yd_px.astype(np.int32)) % SCAN_STEP == 0)          # bool (h, w)

    # Add scanline darkness — clamp to 255
    combined = np.where(on_scan, np.minimum(combined + SCAN_ALPHA, 255), combined)

    # ── 4. Lens glare highlight ───────────────────────────────────────────────
    #
    # A soft elliptical bright spot near the top-centre of the screen,
    # simulating light reflecting off the convex CRT glass.
    # Implemented as a *separate* white RGBA layer composited additively.
    #
    glare_cx = w * 0.50
    glare_cy = h * GLARE_POS
    glare_rx = w * 0.28          # horizontal radius of the glare blob
    glare_ry = h * 0.14          # vertical radius

    xg = (xx - glare_cx) / glare_rx
    yg = (yy - glare_cy) / glare_ry
    glare_r2 = xg * xg + yg * yg

    # Gaussian fall-off; fully zero outside radius 1
    glare_alpha = np.where(
        glare_r2 < 4.0,
        GLARE_A * np.exp(-glare_r2 * 1.2),
        0.0,
    ).astype(np.uint8)

    # ── 5. Assemble final RGBA image ──────────────────────────────────────────
    #
    # Dark layer (vignette + corners + curved scanlines)
    final_dark = np.clip(combined, 0, 255).astype(np.uint8)

    # Start with fully transparent black
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 3] = final_dark          # black, variable alpha = darkening

    out = Image.fromarray(rgba, "RGBA")

    # Composite the glare highlight on top (white, additive)
    glare_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glare_arr = np.zeros((h, w, 4), dtype=np.uint8)
    glare_arr[:, :, 0] = 255            # R
    glare_arr[:, :, 1] = 255            # G
    glare_arr[:, :, 2] = 255            # B
    glare_arr[:, :, 3] = glare_alpha    # A (variable)
    glare_img = Image.fromarray(glare_arr, "RGBA")

    # Alpha-composite: glare on top of dark overlay
    out = Image.alpha_composite(out, glare_img)
    return out


def _build_overlay_slow(w: int, h: int) -> Image.Image:
    """Pure-PIL fallback (no numpy). Fisheye effect is omitted; only vignette."""
    vig = Image.new("L", (w, h), 0)
    vd  = ImageDraw.Draw(vig)
    for i in range(EDGE_FADE):
        t = i / EDGE_FADE
        a = int(VIGNETTE_A * (1.0 - t) ** 2.0)
        vd.rectangle([i, i, w - 1 - i, h - 1 - i], outline=a)
    vig = vig.filter(ImageFilter.GaussianBlur(radius=EDGE_FADE * 0.4))

    corner = Image.new("L", (w, h), 255)
    ImageDraw.Draw(corner).rounded_rectangle(
        [0, 0, w - 1, h - 1], radius=CORNER_R, fill=0
    )
    corner = corner.filter(ImageFilter.GaussianBlur(radius=5))

    combined = Image.new("L", (w, h), 0)
    for y in range(h):
        for x in range(w):
            combined.putpixel(
                (x, y),
                min(255, max(vig.getpixel((x, y)), corner.getpixel((x, y))))
            )
    for y in range(0, h, SCAN_STEP):
        for x in range(w):
            old = combined.getpixel((x, y))
            combined.putpixel((x, y), min(255, old + SCAN_ALPHA))

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.putalpha(combined)
    return out


# pick fastest available implementation
try:
    import numpy as _np
    _build = _build_overlay_fast
except ImportError:
    _build = _build_overlay_slow


class FisheyeOverlay:
    """
    CRT vignette + barrel-distorted scanlines + lens glare,
    rendered as a canvas overlay inside the parent window.

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
            bg=parent.cget("bg"),
            cursor="",
        )

        if enabled:
            self._show()
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
            self._last_wh = (0, 0)   # force rebuild
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
        tk.Misc.lift(self._canvas)
        self._schedule()

    def _bind_passthrough(self):
        """
        Re-dispatch every mouse event to the actual widget under the cursor,
        skipping the canvas itself, so the overlay is invisible to interaction.
        """
        def _forward(event):
            target = event.widget.winfo_containing(event.x_root, event.y_root)
            if target and target is not self._canvas:
                try:
                    target.event_generate(
                        event.type.name if hasattr(event.type, "name") else str(event.type),
                        x=event.x, y=event.y,
                        rootx=event.x_root, rooty=event.y_root,
                        delta=getattr(event, "delta", 0),
                        state=event.state,
                    )
                except Exception:
                    pass

        def _forward_scroll(event):
            target = event.widget.winfo_containing(event.x_root, event.y_root)
            if target and target is not self._canvas:
                try:
                    target.event_generate(
                        "<MouseWheel>",
                        delta=event.delta,
                        x=event.x, y=event.y,
                        rootx=event.x_root, rooty=event.y_root,
                    )
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
        tk.Misc.lift(self._canvas)

    def _schedule(self):
        self._refresh()
        self._job = self._parent.after(REFRESH_MS, self._schedule)