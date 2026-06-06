"""
fisheye_overlay.py  —  CRT vignette + fisheye bulge overlay.
No screenshots, no Toplevel.

How it works
------------
A Canvas with bg='' is placed over the entire parent window using place().
bg='' tells Tk not to paint the canvas background at all, so the sibling
widgets rendered beneath it remain visible through the undrawn areas.

The CRT effects are drawn as individual Canvas items:
  • Barrel-distorted scanlines  — create_line with curved point arrays
  • Vignette                    — stipple-filled bands at each edge
  • Lens glare highlight        — stipple-filled oval near the top
  • Rounded corner masks        — filled arcs at each corner

Mouse events that hit the canvas are caught and re-dispatched to whichever
widget sits underneath so clicking, dragging, and scrolling still work.
"""

import tkinter as tk
import math

# ── tunables ─────────────────────────────────────────────────────────────
EDGE_FADE      = 52      # vignette depth from each edge in pixels
VIGNETTE_RINGS = 7       # number of concentric stipple bands
CORNER_R       = 28      # corner-mask radius in pixels

BARREL_K       = 0.18    # barrel-distortion strength (0 = flat, 0.3 = strong)
SCAN_STEP      = 3       # rows between scanlines
SCAN_SAMPLES   = 30      # horizontal sample points per scanline curve

GLARE_POS      = 0.26    # glare centre as fraction of window height
GLARE_WIDTH    = 0.28    # glare width as fraction of window width
GLARE_HEIGHT   = 0.12    # glare height as fraction of window height
REFRESH_MS     = 350     # ms between layout checks (resize guard)
# ────────────────────────────────────────────────────────────────────────

# Stipple gets *less* dense from outside (ring 0) → inside (ring N-1).
# gray75 = 75 % opaque, gray12 = 12 % opaque.
_STIPPLE = ["gray75", "gray75", "gray50", "gray50", "gray25", "gray12", "gray12"]


class FisheyeOverlay:
    """
    CRT overlay drawn as Canvas items on a background-less Canvas.
    The Canvas bg='' prevents the widget from painting its own background,
    so the content widgets beneath show through untouched areas.
    """

    _FORWARD = (
        "<Button-1>", "<ButtonRelease-1>", "<B1-Motion>",
        "<Button-2>", "<ButtonRelease-2>",
        "<Button-3>", "<ButtonRelease-3>",
        "<MouseWheel>", "<Double-Button-1>",
        "<Enter>", "<Leave>",
    )

    def __init__(self, parent: tk.Tk, enabled: bool = True,
                 scan_color: str = "#000000"):
        self._parent     = parent
        self._enabled    = enabled
        self._job        = None
        self._last_wh    = (0, 0)
        self._scan_color = scan_color

        # bg='' → Tk skips painting the canvas background entirely,
        # letting already-drawn sibling widgets remain visible.
        # If the empty string is rejected (rare), fall back to window bg.
        try:
            self._canvas = tk.Canvas(
                parent, bg="",
                highlightthickness=0, borderwidth=0,
            )
        except tk.TclError:
            self._canvas = tk.Canvas(
                parent, bg=parent.cget("bg"),
                highlightthickness=0, borderwidth=0,
            )

        if enabled:
            self._show()
        self._bind_passthrough()

    # ── public ────────────────────────────────────────────────────────────

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
            if self._job:
                self._parent.after_cancel(self._job)
                self._job = None
            self._canvas.place_forget()
        else:
            self._last_wh = (0, 0)   # force full redraw
            self._show()

    def destroy(self):
        if self._job:
            self._parent.after_cancel(self._job)
            self._job = None
        try:
            self._canvas.destroy()
        except tk.TclError:
            pass

    # ── internal ───────────────────────────────────────────────────────────

    def _show(self):
        self._canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        tk.Misc.lift(self._canvas)
        self._schedule()

    def _bind_passthrough(self):
        """Re-dispatch mouse events to the real widget under the pointer."""
        def _forward(event):
            target = event.widget.winfo_containing(event.x_root, event.y_root)
            if target and target is not self._canvas:
                try:
                    target.event_generate(
                        event.type.name if hasattr(event.type, "name")
                        else str(event.type),
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

    # ── drawing ──────────────────────────────────────────────────────────

    def _draw_crt(self, w: int, h: int):
        """Build all CRT canvas items from scratch."""
        c = self._canvas
        c.delete("crt")

        cx, cy = w / 2.0, h / 2.0
        k      = BARREL_K

        # ── 1. Barrel-distorted scanlines ─────────────────────────────────────
        #
        # Forward barrel map (source → screen):
        #   screen_yn = yn0 * (1 + k * (sxn² + yn0²))
        #
        # A flat horizontal line in source space bows OUTWARD on screen,
        # giving the classic CRT convex-dome appearance.
        #
        step_xn = 2.0 / SCAN_SAMPLES
        for y0 in range(0, h + SCAN_STEP, SCAN_STEP):
            yn0 = (y0 - cy) / cy
            pts = []
            for i in range(SCAN_SAMPLES + 1):
                sxn = -1.0 + i * step_xn
                syn = yn0 * (1.0 + k * (sxn * sxn + yn0 * yn0))
                pts.append(sxn * cx + cx)
                pts.append(syn * cy + cy)
            if len(pts) >= 4:
                c.create_line(
                    pts,
                    fill=self._scan_color,
                    width=1,
                    smooth=True,
                    tags="crt",
                )

        # ── 2. Vignette — concentric stipple bands at each edge ───────────────
        #
        # Ring 0 is the outermost (darkest / highest stipple density).
        # Ring N-1 is the innermost (lightest / lowest stipple density).
        #
        band = max(1, EDGE_FADE // VIGNETTE_RINGS)
        for ring in range(VIGNETTE_RINGS):
            stip  = _STIPPLE[min(ring, len(_STIPPLE) - 1)]
            outer = ring * band
            inner = (ring + 1) * band
            # Top strip
            c.create_rectangle(0, outer, w, inner,
                                fill="black", outline="", stipple=stip, tags="crt")
            # Bottom strip
            c.create_rectangle(0, h - inner, w, h - outer,
                                fill="black", outline="", stipple=stip, tags="crt")
            # Left strip
            c.create_rectangle(outer, 0, inner, h,
                                fill="black", outline="", stipple=stip, tags="crt")
            # Right strip
            c.create_rectangle(w - inner, 0, w - outer, h,
                                fill="black", outline="", stipple=stip, tags="crt")

        # ── 3. Rounded corner masks ───────────────────────────────────────────
        #
        # Draw a filled black arc at each corner that covers the pixels
        # outside the rounded rectangle, mimicking a CRT bezel curve.
        #
        r = CORNER_R
        corners = [
            (0,     0,     0 + r*2,   r*2,   90,  90),   # top-left
            (w-r*2, 0,     w,         r*2,   0,   90),   # top-right
            (0,     h-r*2, r*2,       h,     180, 90),   # bottom-left
            (w-r*2, h-r*2, w,         h,     270, 90),   # bottom-right
        ]
        for x0, y0, x1, y1, start, extent in corners:
            # Filled quarter-circle mask: outline black arc + filled wedge
            c.create_arc(
                x0, y0, x1, y1,
                start=start, extent=extent,
                style=tk.PIESLICE,
                fill="", outline="black", width=max(2, r // 3),
                tags="crt",
            )

        # ── 4. Lens glare highlight ───────────────────────────────────────────
        #
        # A soft white ellipse near the top-centre simulates light reflecting
        # off the curved CRT glass. Apply barrel distortion to make it follow
        # the fisheye curve naturally.
        #
        gx  = w * 0.50
        gy  = h * GLARE_POS
        grx = w * GLARE_WIDTH / 2.0
        gry = h * GLARE_HEIGHT / 2.0
        
        # Apply barrel distortion to glare oval vertical position
        gyn = (gy - cy) / cy
        gyn_distorted = gyn * (1.0 + k * (gyn * gyn))
        gy_distorted = gyn_distorted * cy + cy
        
        c.create_oval(
            gx - grx, gy_distorted - gry, gx + grx, gy_distorted + gry,
            fill="white", outline="",
            stipple="gray12",
            tags="crt",
        )

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
            self._canvas.config(width=w, height=h)
            self._draw_crt(w, h)

        tk.Misc.lift(self._canvas)

    def _schedule(self):
        self._refresh()
        self._job = self._parent.after(REFRESH_MS, self._schedule)
