"""
fisheye_overlay.py
──────────────────
Whole-widget CRT barrel-distortion overlay for SpotifyWidget.

How it works
------------
1.  A borderless, transparent Toplevel sits exactly on top of the main window.
2.  Every REFRESH_MS milliseconds it:
      a. Takes a screenshot of the main window's screen region via PIL.ImageGrab
         (falls back to pyscreenshot / mss if unavailable).
      b. Applies a barrel / pincushion distortion that makes the flat rectangle
         look like a convex CRT screen (bulge outward at the edges).
      c. Renders rounded corners so the four corners fade to the desktop.
      d. Blits the result onto a canvas in the Toplevel — this is the "lens".
3.  All mouse events are passed through to the window below so dragging,
    clicking and scrolling keep working normally.

Only changes related to the fisheye / CRT effect are here.
"""

import tkinter as tk
from PIL import Image, ImageDraw, ImageTk

# ── tunables ──────────────────────────────────────────────────────────────────
REFRESH_MS   = 50          # overlay repaint interval (ms)  ~20 fps
STRENGTH     = 0.18        # barrel distortion strength (0 = none, 0.3 = heavy)
CORNER_R     = 18          # rounded-corner radius (pixels)
# ─────────────────────────────────────────────────────────────────────────────


def _build_lut(w: int, h: int, strength: float):
    """
    Pre-compute a pixel-coordinate look-up table for barrel distortion.

    Returns two flat lists (src_xs, src_ys) of length w*h.
    For each destination pixel (dx, dy) the source pixel is stored.
    Pixels that map outside [0,w)×[0,h) get clamped to the border.
    """
    cx, cy = w / 2.0, h / 2.0
    # Normalise by half the *diagonal* so the effect is equal on both axes
    norm   = (cx**2 + cy**2) ** 0.5

    src_xs = []
    src_ys = []

    for dy in range(h):
        for dx in range(w):
            # Normalised offset from centre  (-1 … +1 range)
            nx = (dx - cx) / norm
            ny = (dy - cy) / norm

            r2     = nx * nx + ny * ny
            # Inverse barrel: map destination → source
            # source coords are *pulled inward* so the rendered image bulges outward
            factor = 1.0 + strength * r2

            sx = int(cx + nx * factor * norm)
            sy = int(cy + ny * factor * norm)

            # Clamp
            src_xs.append(max(0, min(w - 1, sx)))
            src_ys.append(max(0, min(h - 1, sy)))

    return src_xs, src_ys


def _apply_lut(img: Image.Image, lut_xs, lut_ys) -> Image.Image:
    """Apply a pre-computed LUT to an RGB image."""
    w, h   = img.size
    src    = img.tobytes()          # flat bytes, 3 bytes per pixel
    out    = bytearray(w * h * 3)
    stride = w * 3

    for i, (sx, sy) in enumerate(zip(lut_xs, lut_ys)):
        src_off = sy * stride + sx * 3
        dst_off = i * 3
        out[dst_off]     = src[src_off]
        out[dst_off + 1] = src[src_off + 1]
        out[dst_off + 2] = src[src_off + 2]

    return Image.frombytes("RGB", (w, h), bytes(out))


def _rounded_mask(w: int, h: int, r: int) -> Image.Image:
    """RGBA mask: white inside the rounded rect, black in corners."""
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    return mask


class FisheyeOverlay:
    """
    Transparent Toplevel that renders a barrel-distorted copy of the
    parent window on top of it, creating the CRT-bulge illusion.
    """

    def __init__(self, parent: tk.Tk, enabled: bool = True):
        self._parent  = parent
        self._enabled = enabled
        self._job     = None          # after() handle
        self._photo   = None          # keep reference so GC doesn't collect it
        self._lut     = None          # (xs, ys, w, h) cached LUT
        self._mask    = None          # (mask_img, w, h) cached mask

        # ── Overlay window ──────────────────────────────────────────────
        self._top = tk.Toplevel(parent)
        self._top.overrideredirect(True)
        self._top.attributes("-topmost", True)
        # Transparent background colour — anything with this colour is see-through
        self._top.configure(bg="#010101")
        try:
            self._top.attributes("-transparentcolor", "#010101")
        except tk.TclError:
            pass   # not all platforms support this; effect degrades gracefully

        # Pass *all* mouse events through to the window below
        try:
            self._top.attributes("-disabled", True)   # Windows / some Linux WMs
        except tk.TclError:
            pass

        self._canvas = tk.Canvas(
            self._top, bg="#010101",
            highlightthickness=0, borderwidth=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._place_overlay()
        self._schedule()

    # ── Public API ────────────────────────────────────────────────────────

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
            # Clear canvas immediately so the flat widget shows through
            self._canvas.delete("all")
        else:
            self._refresh()

    def destroy(self):
        if self._job:
            self._parent.after_cancel(self._job)
            self._job = None
        try:
            self._top.destroy()
        except tk.TclError:
            pass

    # ── Internal ──────────────────────────────────────────────────────────

    def _place_overlay(self):
        """Size and position the overlay exactly over the parent."""
        x = self._parent.winfo_x()
        y = self._parent.winfo_y()
        w = self._parent.winfo_width()
        h = self._parent.winfo_height()
        self._top.geometry(f"{w}x{h}+{x}+{y}")

    def _get_lut(self, w: int, h: int):
        if self._lut and self._lut[2] == w and self._lut[3] == h:
            return self._lut[0], self._lut[1]
        xs, ys      = _build_lut(w, h, STRENGTH)
        self._lut   = (xs, ys, w, h)
        return xs, ys

    def _get_mask(self, w: int, h: int):
        if self._mask and self._mask[1] == w and self._mask[2] == h:
            return self._mask[0]
        m           = _rounded_mask(w, h, CORNER_R)
        self._mask  = (m, w, h)
        return m

    def _grab_parent(self) -> Image.Image | None:
        """Screenshot just the parent window's region."""
        try:
            from PIL import ImageGrab
            x  = self._parent.winfo_rootx()
            y  = self._parent.winfo_rooty()
            w  = self._parent.winfo_width()
            h  = self._parent.winfo_height()
            if w < 10 or h < 10:
                return None
            return ImageGrab.grab(bbox=(x, y, x + w, y + h))
        except Exception:
            return None

    def _refresh(self):
        if not self._enabled:
            return

        self._place_overlay()

        src = self._grab_parent()
        if src is None:
            return

        w, h = src.size
        src  = src.convert("RGB")

        # Barrel distortion
        lut_xs, lut_ys = self._get_lut(w, h)
        distorted      = _apply_lut(src, lut_xs, lut_ys)

        # Rounded corners via RGBA mask
        mask      = self._get_mask(w, h)
        rgba      = distorted.convert("RGBA")
        # Set alpha from mask: corners become transparent (→ see-through background)
        r, g, b, a = rgba.split()
        rgba      = Image.merge("RGBA", (r, g, b, mask))

        # Blit onto canvas
        self._photo = ImageTk.PhotoImage(rgba)
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)

    def _schedule(self):
        self._refresh()
        self._job = self._parent.after(REFRESH_MS, self._schedule)
