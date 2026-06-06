"""
fisheye_overlay.py  —  CRT barrel-distortion overlay, no flicker, no feedback.
"""

import sys
import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageTk

REFRESH_MS = 50
STRENGTH   = 0.07    # subtle CRT bulge — increase toward 0.18 for more warp
CORNER_R   = 22      # rounded corner radius
EDGE_FADE  = 14      # pixels of soft feather at the border (higher = smoother)


# ── OS-native window grab ─────────────────────────────────────────────────────

def _grab_hwnd(hwnd, w, h):
    """Windows: PrintWindow into a DIB — never includes the overlay."""
    try:
        import ctypes
        gdi = ctypes.windll.gdi32
        usr = ctypes.windll.user32

        hdc    = usr.GetDC(hwnd)
        mem_dc = gdi.CreateCompatibleDC(hdc)
        bmp    = gdi.CreateCompatibleBitmap(hdc, w, h)
        gdi.SelectObject(mem_dc, bmp)
        usr.PrintWindow(hwnd, mem_dc, 2)   # 2 = PW_RENDERFULLCONTENT

        buf = (ctypes.c_char * (w * h * 4))()
        gdi.GetBitmapBits(bmp, w * h * 4, buf)
        gdi.DeleteObject(bmp)
        gdi.DeleteDC(mem_dc)
        usr.ReleaseDC(hwnd, hdc)

        # DIB is BGRA bottom-up; stride=-1 corrects vertical flip.
        # PrintWindow on Windows also mirrors horizontally, so flip that too.
        img = Image.frombytes("RGBA", (w, h), bytes(buf), "raw", "BGRA", 0, -1)
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        return img.convert("RGB")
    except Exception as e:
        print(f"[fisheye] hwnd grab failed: {e}")
        return None


def _grab_xid(xid, w, h):
    """Linux/X11: XGetImage on the window XID."""
    try:
        from Xlib import display as Xd, X
        d   = Xd.Display()
        win = d.create_resource_object("window", xid)
        raw = win.get_image(0, 0, w, h, X.ZPixmap, 0xFFFFFFFF)
        img = Image.frombytes("RGBA", (w, h), raw.data, "raw", "BGRA")
        return img.convert("RGB")
    except Exception as e:
        print(f"[fisheye] xid grab failed: {e}")
        return None


def _grab_native(parent, w, h):
    plat = sys.platform
    if plat == "win32":
        return _grab_hwnd(parent.winfo_id(), w, h)
    if plat.startswith("linux"):
        return _grab_xid(parent.winfo_id(), w, h)
    return None


# ── distortion ────────────────────────────────────────────────────────────────

def _build_lut(w, h, strength):
    cx, cy = w / 2.0, h / 2.0
    norm   = (cx ** 2 + cy ** 2) ** 0.5
    xs, ys = [], []
    for dy in range(h):
        for dx in range(w):
            nx = (dx - cx) / norm
            ny = (dy - cy) / norm
            f  = 1.0 + strength * (nx * nx + ny * ny)
            xs.append(max(0, min(w - 1, int(cx + nx * f * norm))))
            ys.append(max(0, min(h - 1, int(cy + ny * f * norm))))
    return xs, ys


def _apply_lut(img, xs, ys):
    w, h   = img.size
    src    = img.tobytes()
    out    = bytearray(w * h * 3)
    stride = w * 3
    for i, (sx, sy) in enumerate(zip(xs, ys)):
        s = sy * stride + sx * 3
        d = i * 3
        out[d : d + 3] = src[s : s + 3]
    return Image.frombytes("RGB", (w, h), bytes(out))


def _soft_mask(w, h, r, fade):
    """
    Rounded-rect mask with a feathered/anti-aliased edge.
    Draw at 4× scale with generous inset, blur heavily, then downsample
    via LANCZOS — produces smooth sub-pixel corner feathering.
    """
    scale = 4
    big_w, big_h = w * scale, h * scale
    big_r = r * scale
    # Inset the filled rect so the blur has room to fade to zero at the edge
    inset = fade * scale

    m = Image.new("L", (big_w, big_h), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        [inset, inset, big_w - 1 - inset, big_h - 1 - inset],
        radius=big_r, fill=255,
    )
    m = m.filter(ImageFilter.GaussianBlur(radius=inset * 0.9))
    m = m.resize((w, h), Image.LANCZOS)
    return m


# ── overlay ───────────────────────────────────────────────────────────────────

class FisheyeOverlay:
    def __init__(self, parent: tk.Tk, enabled: bool = True):
        self._parent       = parent
        self._enabled      = enabled
        self._job          = None
        self._photo        = None
        self._lut          = None
        self._mask         = None
        self._last_raw     = None
        self._native_ok    = True

        self._top = tk.Toplevel(parent)
        self._top.overrideredirect(True)
        self._top.attributes("-topmost", True)
        self._top.configure(bg="#010101")
        try:
            self._top.attributes("-transparentcolor", "#010101")
        except tk.TclError:
            pass
        try:
            self._top.attributes("-disabled", True)
        except tk.TclError:
            pass

        self._canvas = tk.Canvas(
            self._top, bg="#010101", highlightthickness=0, borderwidth=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._place_overlay()
        self._schedule()

    # ── public ────────────────────────────────────────────────────────────────

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
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

    # ── internal ──────────────────────────────────────────────────────────────

    def _place_overlay(self):
        x = self._parent.winfo_x()
        y = self._parent.winfo_y()
        w = self._parent.winfo_width()
        h = self._parent.winfo_height()
        self._top.geometry(f"{w}x{h}+{x}+{y}")

    def _get_lut(self, w, h):
        if self._lut and self._lut[2] == w and self._lut[3] == h:
            return self._lut[0], self._lut[1]
        xs, ys    = _build_lut(w, h, STRENGTH)
        self._lut = (xs, ys, w, h)
        return xs, ys

    def _get_mask(self, w, h):
        if self._mask and self._mask[1] == w and self._mask[2] == h:
            return self._mask[0]
        m          = _soft_mask(w, h, CORNER_R, EDGE_FADE)
        self._mask = (m, w, h)
        return m

    def _grab(self, w, h):
        # 1. OS-native (no compositor, overlay invisible to it)
        if self._native_ok:
            img = _grab_native(self._parent, w, h)
            if img is not None:
                return img
            self._native_ok = False   # don't retry on every frame

        # 2. Freeze-frame fallback: reuse last frame while doing the grab
        from PIL import ImageGrab
        try:
            self._top.withdraw()
            self._parent.update()
            x   = self._parent.winfo_rootx()
            y   = self._parent.winfo_rooty()
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h)).convert("RGB")
            return img
        except Exception:
            return self._last_raw
        finally:
            self._top.deiconify()
            self._top.lift()
            self._top.attributes("-topmost", True)

    def _refresh(self):
        if not self._enabled:
            return

        self._place_overlay()
        w = self._parent.winfo_width()
        h = self._parent.winfo_height()
        if w < 10 or h < 10:
            return

        src = self._grab(w, h)
        if src is None:
            return
        self._last_raw = src

        xs, ys    = self._get_lut(w, h)
        distorted = _apply_lut(src, xs, ys)

        mask       = self._get_mask(w, h)
        rgba       = distorted.convert("RGBA")
        r, g, b, a = rgba.split()
        rgba       = Image.merge("RGBA", (r, g, b, mask))

        self._photo = ImageTk.PhotoImage(rgba)
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)

    def _schedule(self):
        self._refresh()
        self._job = self._parent.after(REFRESH_MS, self._schedule)