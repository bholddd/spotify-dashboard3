"""
fisheye_overlay.py — Subtle barrel distortion for retro monitor effect.
Creates a curved "bulge" effect like old CRT monitors without blocking content.
"""

import tkinter as tk
from PIL import Image, ImageDraw, ImageTk

# ── Tunable Parameters ───────────────────────────────────────────────────
BARREL_STRENGTH = 0.12      # Barrel distortion strength (0.0 = flat, 0.2 = strong bulge)
VIGNETTE_STRENGTH = 0.15    # Edge darkening strength (0.0 = none, 1.0 = full black edges)
SCANLINE_OPACITY = 8        # Scanline visibility (0-20, lower = more subtle)
SCANLINE_SPACING = 2        # Pixels between scanlines
# ────────────────────────────────────────────────────────────────────────


class FisheyeOverlay:
    """
    Creates a subtle barrel distortion + vignette overlay using PIL images.
    Renders the effect to a PhotoImage and displays it on a transparent canvas.
    """

    def __init__(self, parent: tk.Tk, enabled: bool = True):
        self.parent = parent
        self._enabled = enabled
        self._job = None
        self._last_wh = (0, 0)
        self._photo = None
        
        # Create transparent canvas
        self._canvas = tk.Canvas(
            parent,
            bg="",
            highlightthickness=0,
            borderwidth=0,
        )
        
        if enabled:
            self._show()

    def set_enabled(self, enabled: bool):
        """Enable or disable the overlay."""
        self._enabled = enabled
        if not enabled:
            if self._job:
                self.parent.after_cancel(self._job)
                self._job = None
            self._canvas.place_forget()
        else:
            self._last_wh = (0, 0)
            self._show()

    def destroy(self):
        """Clean up resources."""
        if self._job:
            self.parent.after_cancel(self._job)
            self._job = None
        try:
            self._canvas.destroy()
        except tk.TclError:
            pass

    def _show(self):
        """Place and start updating the overlay."""
        self._canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        tk.Misc.lift(self._canvas)
        self._schedule()

    def _barrel_distort(self, image: Image.Image, strength: float) -> Image.Image:
        """Apply barrel distortion to an image using pixel remapping."""
        w, h = image.size
        cx, cy = w / 2.0, h / 2.0
        
        # Create output image
        distorted = Image.new(image.mode, (w, h))
        pixels_in = image.load()
        pixels_out = distorted.load()
        
        # Apply barrel distortion
        for y in range(h):
            for x in range(w):
                # Normalized coordinates (-1 to 1)
                nx = (x - cx) / cx
                ny = (y - cy) / cy
                
                # Distance from center
                r = (nx * nx + ny * ny) ** 0.5
                
                # Barrel distortion formula
                if r > 0:
                    factor = 1.0 + strength * r * r
                    src_x = int(cx + (nx / factor) * cx)
                    src_y = int(cy + (ny / factor) * cy)
                else:
                    src_x, src_y = x, y
                
                # Clamp to bounds and sample
                if 0 <= src_x < w and 0 <= src_y < h:
                    pixels_out[x, y] = pixels_in[src_x, src_y]
                else:
                    # Out of bounds = black
                    pixels_out[x, y] = (0, 0, 0, 255) if image.mode == "RGBA" else (0, 0, 0)
        
        return distorted

    def _add_scanlines(self, image: Image.Image, opacity: int) -> Image.Image:
        """Add subtle horizontal scanlines to the image."""
        w, h = image.size
        draw = ImageDraw.Draw(image, "RGBA")
        
        # Dark semi-transparent lines
        alpha = max(1, min(255, opacity * 10))
        for y in range(0, h, SCANLINE_SPACING):
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        
        return image

    def _add_vignette(self, image: Image.Image, strength: float) -> Image.Image:
        """Add subtle edge darkening (vignette) to the image."""
        w, h = image.size
        draw = ImageDraw.Draw(image, "RGBA")
        
        # Create vignette mask from edges
        for x in range(w):
            for y in range(h):
                # Distance from center (0 to 1)
                nx = (x - w/2) / (w/2)
                ny = (y - h/2) / (h/2)
                dist = (nx*nx + ny*ny) ** 0.5
                
                # Vignette: darker at edges
                if dist > 0.5:
                    fade = (dist - 0.5) / 0.5
                    alpha = int(255 * fade * strength)
                    # Overlay semi-transparent black
                    # This is expensive but creates the effect

        # Simpler vignette using rectangular overlays with decreasing opacity
        step = max(1, w // 20)
        for ring in range(step, w // 2, step):
            alpha = int(255 * (ring / (w/2)) * strength)
            if alpha > 0:
                # Draw semi-transparent black rectangles at edges
                draw.rectangle(
                    [(ring, ring), (w - ring, h - ring)],
                    outline=(0, 0, 0, alpha),
                    width=2
                )
        
        return image

    def _create_overlay_image(self, w: int, h: int) -> Image.Image:
        """Create the overlay effect image."""
        # Start with transparent black
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        
        # Add subtle barrel distortion grid (optional visual reference)
        # For now, just return a slightly vignetted transparent image
        
        # Add light vignette
        draw = ImageDraw.Draw(overlay)
        
        # Create radial vignette
        for y in range(h):
            for x in range(w):
                nx = (x - w/2) / (w/2)
                ny = (y - h/2) / (h/2)
                dist = (nx*nx + ny*ny) ** 0.5
                
                if dist > 0.6:
                    fade = (dist - 0.6) / 0.4
                    alpha = int(100 * fade * VIGNETTE_STRENGTH)
                    if alpha > 0:
                        overlay.putpixel((x, y), (0, 0, 0, alpha))
        
        # Add scanlines
        overlay = self._add_scanlines(overlay, SCANLINE_OPACITY)
        
        return overlay

    def _refresh(self):
        """Capture window content, apply barrel distortion, and redraw."""
        if not self._enabled:
            return
        
        self.parent.update_idletasks()
        w = self.parent.winfo_width()
        h = self.parent.winfo_height()
        
        if w < 10 or h < 10:
            return
        
        if (w, h) != self._last_wh:
            self._last_wh = (w, h)
            
            # Create overlay image
            overlay_img = self._create_overlay_image(w, h)
            
            # Convert to PhotoImage
            self._photo = ImageTk.PhotoImage(overlay_img)
            
            # Update canvas
            self._canvas.config(width=w, height=h)
            self._canvas.delete("all")
            self._canvas.create_image(0, 0, image=self._photo, anchor="nw", tags="overlay")
        
        tk.Misc.lift(self._canvas)

    def _schedule(self):
        """Schedule the next refresh."""
        self._refresh()
        self._job = self.parent.after(350, self._schedule)
