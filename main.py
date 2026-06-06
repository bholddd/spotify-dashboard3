"""
Spotify Dashboard Widget — Retro Pixel Edition
Pixelated checkered background, CRT-style themes, Courier New font throughout.
"""

import tkinter as tk
import threading
import json
import os
import sys
import webbrowser
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageTk
from spotify_auth import SpotifyAuthenticator
from spotify_api import SpotifyAPI
from fisheye_overlay import FisheyeOverlay


# ─── Retro font ─────────────────────────────────────────────────────────
FONT = "Courier New"


class SpotifyWidget:
    """Retro Pixel Spotify Dashboard Widget"""

    PALETTES = {
        "terminal": {
            "name": "Terminal",
            "bg":           "#000000",
            "secondary_bg": "#111111",
            "tertiary_bg":  "#001400",
            "fg":           "#00FF41",
            "accent":       "#00AA00",
            "text_secondary": "#007A1F",
            "check1":       "#001400",
            "check2":       "#001C00",
        },
        "amber": {
            "name": "Amber CRT",
            "bg":           "#0D0800",
            "secondary_bg": "#1F1200",
            "tertiary_bg":  "#130A00",
            "fg":           "#FFB000",
            "accent":       "#FF8000",
            "text_secondary": "#AA7000",
            "check1":       "#130A00",
            "check2":       "#1C1000",
        },
        "gameboy": {
            "name": "Game Boy",
            "bg":           "#0F380F",
            "secondary_bg": "#2D5A1C",
            "tertiary_bg":  "#8BAC0F",
            "fg":           "#0F380F",
            "accent":       "#306230",
            "text_secondary": "#1A3A1A",
            "check1":       "#8BAC0F",
            "check2":       "#9BBC0F",
        },
        "synthwave": {
            "name": "Synthwave",
            "bg":           "#0D0020",
            "secondary_bg": "#1A003A",
            "tertiary_bg":  "#08000F",
            "fg":           "#FF00FF",
            "accent":       "#00FFFF",
            "text_secondary": "#BB00BB",
            "check1":       "#08000F",
            "check2":       "#0F0018",
        },
    }

    DEMO_ARTISTS = [
        {"name": "The Weeknd",       "genres": "synth-pop, pop",          "popularity": 92, "url": "https://open.spotify.com/artist/1Xyo4u8uIGMw73CxIaXvj"},
        {"name": "Drake",             "genres": "hip-hop, rap",            "popularity": 88, "url": "https://open.spotify.com/artist/7dGJo4pcD2V6oG8kP0tJt"},
        {"name": "Taylor Swift",      "genres": "pop, country",            "popularity": 95, "url": "https://open.spotify.com/artist/06HL4z0CvFAxyc27GXpf94"},
        {"name": "Ariana Grande",     "genres": "pop, r&b",                "popularity": 90, "url": "https://open.spotify.com/artist/66CXWjxzNUsdJxJ2JdwvnR"},
        {"name": "Post Malone",       "genres": "trap, hip-hop",           "popularity": 85, "url": "https://open.spotify.com/artist/PostMalone"},
        {"name": "Billie Eilish",     "genres": "alternative, indie",      "popularity": 88, "url": "https://open.spotify.com/artist/6qqNVTkY8uBU9cUvJSo"},
        {"name": "Bad Bunny",         "genres": "reggaeton, trap latino",   "popularity": 92, "url": "https://open.spotify.com/artist/BadBunny"},
        {"name": "Harry Styles",      "genres": "pop, rock",               "popularity": 86, "url": "https://open.spotify.com/artist/6deJKheGRHoExMgJeffo01"},
        {"name": "Dua Lipa",          "genres": "pop, dance",              "popularity": 87, "url": "https://open.spotify.com/artist/6HvZYsbFfjnjFrWF950C9m"},
        {"name": "The Chainsmokers",  "genres": "electronic, pop",         "popularity": 80, "url": "https://open.spotify.com/artist/69GGBxA162lQ3FqAJtBjBC"},
        {"name": "Shawn Mendes",      "genres": "pop, pop-rock",           "popularity": 82, "url": "https://open.spotify.com/artist/7n2wHs1TKAczGzO7Dd0qKw"},
        {"name": "Khalid",            "genres": "r&b, pop",                "popularity": 79, "url": "https://open.spotify.com/artist/6LuymHvsWaNTap0EYna"},
        {"name": "Camila Cabello",    "genres": "pop, latin",              "popularity": 81, "url": "https://open.spotify.com/artist/4nDoRrQiYLoBzwC5BhVG0k"},
        {"name": "Alan Walker",       "genres": "electronic, edm",         "popularity": 75, "url": "https://open.spotify.com/artist/7vk4XtFDUKqiaeIWHRSkHt"},
        {"name": "Logic",             "genres": "hip-hop, rap",            "popularity": 77, "url": "https://open.spotify.com/artist/5nCnpMS0Uixt4PSoCMTga7"},
    ]

    DEMO_TRACKS = [
        {"name": "Blinding Lights",      "artist": "The Weeknd",                    "album": "After Hours",               "popularity": 94, "url": "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXV6hS"},
        {"name": "One Dance",            "artist": "Drake ft. Wizkid & Kyla",       "album": "Views",                     "popularity": 91, "url": "https://open.spotify.com/track/1301WleyT98MSxVHP"},
        {"name": "Levitating",           "artist": "Dua Lipa ft. DaBaby",           "album": "Future Nostalgia",          "popularity": 93, "url": "https://open.spotify.com/track/0dGsSpZcaIiOUieK6"},
        {"name": "Shape of You",         "artist": "Ed Sheeran",                    "album": "÷",                         "popularity": 95, "url": "https://open.spotify.com/track/7qiZfU4dY1lsylvN8"},
        {"name": "Peaches",              "artist": "Justin Bieber ft. Daniel Caesar","album": "Justice",                  "popularity": 89, "url": "https://open.spotify.com/track/4cOdK2wGLETKBW3P"},
        {"name": "Anti-Hero",            "artist": "Taylor Swift",                  "album": "Midnights",                 "popularity": 96, "url": "https://open.spotify.com/track/0V3dsPmy4NqIUZSp"},
        {"name": "As It Was",            "artist": "Harry Styles",                  "album": "Harry's House",             "popularity": 92, "url": "https://open.spotify.com/track/7qiZfU4dY1lsylvN"},
        {"name": "Heat Waves",           "artist": "Glass Animals",                 "album": "Dreamland",                 "popularity": 88, "url": "https://open.spotify.com/track/2takcwFXGpVSXi3R"},
        {"name": "Sunroof",              "artist": "Nicky Youre",                   "album": "Sunroof",                   "popularity": 87, "url": "https://open.spotify.com/track/4rVrcmK72nG8eQ5B"},
        {"name": "Running Up That Hill", "artist": "Kate Bush",                     "album": "Stranger Things Vol. 1",    "popularity": 90, "url": "https://open.spotify.com/track/7qIVTtaOfHLSKc0"},
        {"name": "Flowers",             "artist": "Miley Cyrus",                   "album": "Endless Summer Vacation",   "popularity": 91, "url": "https://open.spotify.com/track/4rVrcmK72nG8eQ5Bo"},
        {"name": "Industry Baby",        "artist": "Lil Nas X & Jack Harlow",       "album": "Montero",                   "popularity": 85, "url": "https://open.spotify.com/track/2takcwFXGpVSXi3R"},
        {"name": "Vampire",              "artist": "Olivia Rodrigo",                "album": "GUTS",                      "popularity": 84, "url": "https://open.spotify.com/track/2takcwFXGpVSXi3R"},
        {"name": "Dance the Night",      "artist": "Dua Lipa",                      "album": "Barbie The Album",          "popularity": 89, "url": "https://open.spotify.com/track/2takcwFXGpVSXi3R"},
        {"name": "Cruel Summer",         "artist": "Taylor Swift",                  "album": "Lover",                     "popularity": 92, "url": "https://open.spotify.com/track/7qiZfU4dY1lsylvN"},
    ]

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _contrast_fg(hex_color: str) -> str:
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return "#FFFFFF"
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#000000" if luminance > 0.5 else "#FFFFFF"

    # ── Init ───────────────────────────────────────────────────────────

    def __init__(self, root):
        self.root = root
        self.root.title("Spotify Widget")

        self.widget_width  = 390
        self.widget_height = 390
        self.row_height    = 58
        self.control_height = 58
        self.content_height = self.widget_height - self.control_height

        # State
        self.sp_client     = None
        self.sp_api        = None
        self.current_time_range = "medium_term"
        self.current_tab   = "artists"
        self.drag_data     = {"x": 0, "y": 0}
        self.dragging_enabled = True
        self.loading       = False
        self.artists_data  = []
        self.tracks_data   = []
        self.settings_open = False
        self.demo_mode     = False
        self.image_cache   = {}
        self.item_images   = []
        self.fisheye_enabled = False
        self._fisheye_overlay = None

        # Settings
        self.config_file = "widget_config.json"
        self.settings    = self.load_settings()
        self.current_palette = self.settings.get("palette", "terminal")
        self.fisheye_enabled = self.settings.get("fisheye", False)
        if self.current_palette not in self.PALETTES:
            self.current_palette = "terminal"

        self.setup_styles()

        # Window
        self.root.geometry(f"{self.widget_width}x{self.widget_height}")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        self.root.configure(bg=self.panel_bg)

        # Build UI
        self.create_ui()
        self.setup_drag()
        self.load_window_position()
        self.root.after(50, self.load_window_position)
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after_idle(self.root.attributes, "-topmost", False)

        self.apply_theme_colors()

        # Demo data
        self.demo_mode    = True
        self.artists_data = self.DEMO_ARTISTS
        self.tracks_data  = self.DEMO_TRACKS
        self.display_artists()
        self.display_songs()
        print("Widget loaded with demo data!")

        # Create fisheye overlay only if enabled
        if self.fisheye_enabled:
            self._fisheye_overlay = FisheyeOverlay(self.root, enabled=True)

        # self.authenticate()   # Uncomment to enable live Spotify data

    # ── Settings persistence ──────────────────────────────────────────────────

    def load_settings(self):
        defaults = {"palette": "terminal", "x": None, "y": None, "fisheye": False}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file) as f:
                    defaults.update(json.load(f))
            except Exception:
                pass
        return defaults

    def save_settings(self):
        self.settings["palette"] = self.current_palette
        self.settings["fisheye"] = self.fisheye_enabled
        self.settings["x"] = self.root.winfo_x()
        self.settings["y"] = self.root.winfo_y()
        with open(self.config_file, "w") as f:
            json.dump(self.settings, f, indent=2)

    def load_window_position(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = sw - self.widget_width  - 24
        y  = sh - self.widget_height - 64
        self.root.geometry(f"{self.widget_width}x{self.widget_height}+{x}+{y}")

    # ── Theme ──────────────────────────────────────────────────────────

    def setup_styles(self):
        p = self.PALETTES[self.current_palette]
        self.palette        = p
        self.bg_color       = p["bg"]
        self.secondary_bg   = p["secondary_bg"]
        self.tertiary_bg    = p["tertiary_bg"]
        self.fg_color       = p["fg"]
        self.accent_color   = p["accent"]
        self.text_secondary = p["text_secondary"]
        self.panel_bg       = p["bg"]

    def apply_theme_colors(self):
        self.setup_styles()
        self.update_background_colors()

    def update_background_colors(self):
        for attr in ("main_frame", "content_settings_frame"):
            if hasattr(self, attr):
                getattr(self, attr).configure(bg=self.panel_bg)
        for attr in ("content_frame", "artists_canvas", "artists_content",
                     "songs_canvas", "songs_content"):
            if hasattr(self, attr):
                getattr(self, attr).configure(bg=self.tertiary_bg)

    def change_palette(self, palette_name):
        reopen = self.settings_open
        self.current_palette = palette_name
        self.setup_styles()
        for w in self.root.winfo_children():
            w.destroy()
        self.root.configure(bg=self.panel_bg)
        self.create_ui()
        if self.artists_data:
            self.display_artists()
        if self.tracks_data:
            self.display_songs()
        if reopen:
            self.open_settings()

    def toggle_fisheye(self):
        self.fisheye_enabled = not self.fisheye_enabled
        if self.fisheye_enabled:
            if self._fisheye_overlay is None:
                self._fisheye_overlay = FisheyeOverlay(self.root, enabled=True)
            else:
                self._fisheye_overlay.set_enabled(True)
        else:
            if self._fisheye_overlay is not None:
                self._fisheye_overlay.set_enabled(False)
        # Re-open settings panel so the ON/OFF label refreshes immediately
        if self.settings_open:
            self.open_settings()

    # ── UI construction ───────────────────────────────────────────────────────

    def create_ui(self):
        main_frame = tk.Frame(self.root, bg=self.panel_bg)
        main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame = main_frame

        self.content_settings_frame = tk.Frame(main_frame, bg=self.panel_bg)
        self.content_settings_frame.pack(fill=tk.BOTH, expand=True)

        self.content_frame = tk.Frame(
            self.content_settings_frame, bg=self.tertiary_bg,
            height=self.content_height
        )
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        self.content_frame.pack_propagate(False)

        border_line = tk.Frame(main_frame, bg=self.accent_color, height=2)
        border_line.pack(fill=tk.X, side=tk.BOTTOM)

        self.control_frame = tk.Frame(main_frame, bg=self.secondary_bg)
        self.control_frame.pack(fill=tk.X, side=tk.BOTTOM)

        btn_row = tk.Frame(self.control_frame, bg=self.secondary_bg)
        btn_row.pack(fill=tk.X, padx=4, pady=6)

        self.tab_buttons = {}
        for label, tab_name in [("ARTISTS", "artists"), ("SONGS", "songs")]:
            btn = self._make_btn(btn_row, label, lambda n=tab_name: self.change_tab(n))
            btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
            self.tab_buttons[tab_name] = btn

        self.time_buttons = {}
        for label, code in [("1W", "short_term"), ("1M", "medium_term"), ("6M", "long_term")]:
            btn = self._make_btn(btn_row, label, lambda c=code: self.change_time_range(c))
            btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
            self.time_buttons[code] = btn

        settings_btn = self._make_btn(btn_row, "SET", self.toggle_settings)
        settings_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.settings_btn = settings_btn

        self.update_control_states()

        self.artists_canvas = tk.Canvas(
            self.content_frame, bg=self.tertiary_bg,
            highlightthickness=0, borderwidth=0, relief="flat"
        )
        self.artists_canvas.pack(fill=tk.BOTH, expand=True)
        self.artists_content = tk.Frame(self.artists_canvas, bg=self.tertiary_bg)
        self.artists_window = self.artists_canvas.create_window(
            (0, 0), window=self.artists_content, anchor=tk.NW
        )

        self.songs_canvas = tk.Canvas(
            self.content_frame, bg=self.tertiary_bg,
            highlightthickness=0, borderwidth=0, relief="flat"
        )
        self.songs_content = tk.Frame(self.songs_canvas, bg=self.tertiary_bg)
        self.songs_window = self.songs_canvas.create_window(
            (0, 0), window=self.songs_content, anchor=tk.NW
        )

        self.canvases = {
            "artists": (self.artists_canvas, self.artists_content),
            "songs":   (self.songs_canvas,   self.songs_content),
        }

        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.artists_canvas.pack(fill=tk.BOTH, expand=True)

        self.settings_frame = tk.Frame(self.content_settings_frame, bg=self.secondary_bg)

    def _make_btn(self, parent, text, command):
        fg = self._contrast_fg(self.tertiary_bg)
        return tk.Button(
            parent,
            text=text,
            font=(FONT, 7, "bold"),
            bg=self.tertiary_bg,
            fg=self.fg_color,
            activebackground=self.accent_color,
            activeforeground=self._contrast_fg(self.accent_color),
            border=1,
            relief=tk.RAISED,
            padx=4,
            pady=5,
            command=command,
        )

    def update_control_states(self):
        if not hasattr(self, "tab_buttons"):
            return
        for tab, btn in self.tab_buttons.items():
            active = tab == self.current_tab
            btn.config(
                relief=tk.SUNKEN if active else tk.RAISED,
                bg=self.accent_color if active else self.tertiary_bg,
                fg=self._contrast_fg(self.accent_color) if active else self.fg_color,
            )
        for code, btn in self.time_buttons.items():
            active = code == self.current_time_range
            btn.config(
                relief=tk.SUNKEN if active else tk.RAISED,
                bg=self.accent_color if active else self.tertiary_bg,
                fg=self._contrast_fg(self.accent_color) if active else self.fg_color,
            )

    def _draw_checkered_bg(self, canvas):
        canvas.delete("checker")
        c1 = self.palette.get("check1", self.tertiary_bg)
        c2 = self.palette.get("check2", self.bg_color)
        sz = 8
        total_items = max(len(self.artists_data), len(self.tracks_data), 15)
        h = total_items * self.row_height + self.content_height
        w = self.widget_width + sz

        for row in range(0, h // sz + 2):
            for col in range(0, w // sz + 2):
                color = c1 if (row + col) % 2 == 0 else c2
                canvas.create_rectangle(
                    col * sz, row * sz,
                    col * sz + sz, row * sz + sz,
                    fill=color, outline="", tags="checker",
                )
        canvas.tag_lower("checker")

    # ── Settings panel ───────────────────────────────────────────────────────

    def toggle_settings(self):
        if self.settings_open:
            self.close_settings()
        else:
            self.open_settings()

    def open_settings(self):
        self.settings_open    = True
        self.dragging_enabled = False
        self.settings_btn.config(
            relief=tk.SUNKEN,
            bg=self.accent_color,
            fg=self._contrast_fg(self.accent_color),
        )
        self.content_frame.pack_forget()

        for w in self.settings_frame.winfo_children():
            w.destroy()
        self.settings_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            self.settings_frame,
            text="[ SETTINGS ]",
            font=(FONT, 11, "bold"),
            bg=self.secondary_bg,
            fg=self.fg_color,
        ).pack(pady=10)

        tk.Frame(self.settings_frame, bg=self.accent_color, height=1).pack(
            fill=tk.X, padx=10, pady=(0, 8)
        )

        tk.Label(
            self.settings_frame,
            text="> COLOR THEME",
            font=(FONT, 8, "bold"),
            bg=self.secondary_bg,
            fg=self.text_secondary,
        ).pack(anchor=tk.W, padx=14, pady=(4, 4))

        pal_frame = tk.Frame(self.settings_frame, bg=self.secondary_bg)
        pal_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        for pal_key in self.PALETTES:
            pal     = self.PALETTES[pal_key]
            selected = pal_key == self.current_palette
            btn_bg  = self.accent_color if selected else self.tertiary_bg
            btn_fg  = self._contrast_fg(btn_bg)
            tk.Button(
                pal_frame,
                text=pal["name"],
                font=(FONT, 7, "bold"),
                bg=btn_bg,
                fg=btn_fg,
                activebackground=self.accent_color,
                activeforeground=self._contrast_fg(self.accent_color),
                border=1,
                relief=tk.SUNKEN if selected else tk.RAISED,
                padx=6,
                pady=3,
                command=lambda k=pal_key: self.change_palette(k),
            ).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        tk.Frame(self.settings_frame, bg=self.accent_color, height=1).pack(
            fill=tk.X, padx=10, pady=4
        )

        fisheye_status = "ON" if self.fisheye_enabled else "OFF"
        fisheye_color  = self.fg_color if self.fisheye_enabled else self.text_secondary
        tk.Label(
            self.settings_frame,
            text=f"> FISHEYE: {fisheye_status}",
            font=(FONT, 8),
            bg=self.secondary_bg,
            fg=fisheye_color,
        ).pack(anchor=tk.W, padx=14, pady=(4, 4))

        fisheye_btn_bg = self.accent_color if self.fisheye_enabled else self.tertiary_bg
        fisheye_btn_fg = self._contrast_fg(fisheye_btn_bg)
        tk.Button(
            self.settings_frame,
            text="TOGGLE FISHEYE",
            font=(FONT, 7, "bold"),
            bg=fisheye_btn_bg,
            fg=fisheye_btn_fg,
            activebackground=self.accent_color,
            activeforeground=self._contrast_fg(self.accent_color),
            border=1,
            relief=tk.RAISED,
            padx=6,
            pady=3,
            command=self.toggle_fisheye,
        ).pack(padx=10, pady=(0, 10), fill=tk.X)

        tk.Frame(self.settings_frame, bg=self.accent_color, height=1).pack(
            fill=tk.X, padx=10, pady=4
        )
        mode_text  = "DEMO MODE" if self.demo_mode else "LIVE DATA"
        mode_color = self.text_secondary if self.demo_mode else self.fg_color
        tk.Label(
            self.settings_frame,
            text=f"> MODE: {mode_text}",
            font=(FONT, 8),
            bg=self.secondary_bg,
            fg=mode_color,
        ).pack(anchor=tk.W, padx=14, pady=4)

        tk.Button(
            self.settings_frame,
            text="[ CLOSE ]",
            font=(FONT, 9, "bold"),
            bg=self.accent_color,
            fg=self._contrast_fg(self.accent_color),
            activebackground=self.fg_color,
            activeforeground=self._contrast_fg(self.fg_color),
            border=1,
            relief=tk.RAISED,
            padx=20,
            pady=6,
            command=self.close_settings,
        ).pack(pady=10)

    def close_settings(self):
        self.settings_open    = False
        self.dragging_enabled = True
        self.settings_btn.config(
            relief=tk.RAISED,
            bg=self.tertiary_bg,
            fg=self.fg_color,
        )
        self.settings_frame.pack_forget()
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        self.save_settings()
        self.update_control_states()

    # ── Tab / time-range navigation ───────────────────────────────────────────

    def change_tab(self, tab_name):
        self.current_tab = tab_name
        self.update_control_states()
        for canvas, _ in self.canvases.values():
            canvas.pack_forget()
        canvas, _ = self.canvases[tab_name]
        canvas.pack(fill=tk.BOTH, expand=True)

    def change_time_range(self, time_code):
        self.current_time_range = time_code
        self.update_control_states()
        if not self.demo_mode:
            self.load_data()

    # ── Drag ───────────────────────────────────────────────────────────

    def setup_drag(self):
        self.root.bind("<Button-1>",        self.drag_start)
        self.root.bind("<B1-Motion>",       self.drag_motion)
        self.root.bind("<ButtonRelease-1>", self.drag_stop)

    def drag_start(self, event):
        if self.dragging_enabled:
            self.drag_data["x"] = event.x_root - self.root.winfo_x()
            self.drag_data["y"] = event.y_root - self.root.winfo_y()

    def drag_motion(self, event):
        if self.dragging_enabled:
            x = event.x_root - self.drag_data["x"]
            y = event.y_root - self.drag_data["y"]
            self.root.geometry(f"+{x}+{y}")

    def drag_stop(self, event):
        if self.dragging_enabled:
            self.save_settings()

    def _on_mousewheel(self, event):
        if self.settings_open:
            return
        if self.current_tab == "artists":
            self.artists_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            self.songs_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── Spotify auth / data ───────────────────────────────────────────────────

    def authenticate(self):
        threading.Thread(target=self._authenticate_thread, daemon=True).start()

    def _authenticate_thread(self):
        try:
            auth = SpotifyAuthenticator()
            self.sp_client = auth.get_spotify_client()
            self.sp_api    = SpotifyAPI(self.sp_client)
            self.load_data()
        except Exception as e:
            print(f"Auth error (demo mode): {e}")

    def load_data(self):
        if not self.sp_api:
            return
        self.loading = True
        threading.Thread(target=self._load_data_thread, daemon=True).start()

    def _load_data_thread(self):
        try:
            artists = self.sp_api.get_top_artists(self.current_time_range, limit=15)
            tracks  = self.sp_api.get_top_tracks(self.current_time_range, limit=15)
            if artists and tracks:
                self.artists_data = artists
                self.tracks_data  = tracks
                self.demo_mode    = False
                self.root.after(0, self.display_artists)
                self.root.after(0, self.display_songs)
                print("Switched to live data!")
        except Exception as e:
            print(f"Data load error (demo): {e}")
        finally:
            self.loading = False

    # ── Display ──────────────────────────────────────────────────────────

    def display_artists(self):
        self.item_images = []
        for w in self.artists_content.winfo_children():
            w.destroy()
        if not self.artists_data:
            return
        self._draw_checkered_bg(self.artists_canvas)
        for idx, artist in enumerate(self.artists_data, 1):
            self._create_artist_row(idx, artist)
        self.artists_content.update_idletasks()
        self.artists_canvas.configure(scrollregion=self.artists_canvas.bbox("all"))
        self.artists_canvas.itemconfigure(self.artists_window, width=self.widget_width)

    def display_songs(self):
        self.item_images = []
        for w in self.songs_content.winfo_children():
            w.destroy()
        if not self.tracks_data:
            return
        self._draw_checkered_bg(self.songs_canvas)
        for idx, track in enumerate(self.tracks_data, 1):
            self._create_track_row(idx, track)
        self.songs_content.update_idletasks()
        self.songs_canvas.configure(scrollregion=self.songs_canvas.bbox("all"))
        self.songs_canvas.itemconfigure(self.songs_window, width=self.widget_width)

    def load_item_image(self, image_url, size=38):
        if not image_url:
            return None
        key = (image_url, size)
        if key in self.image_cache:
            return self.image_cache[key]
        try:
            resp = requests.get(image_url, timeout=5)
            resp.raise_for_status()
            img  = Image.open(BytesIO(resp.content)).convert("RGB")
            img.thumbnail((size, size), Image.LANCZOS)
            square = Image.new("RGB", (size, size), self.tertiary_bg)
            square.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
            photo = ImageTk.PhotoImage(square)
            self.image_cache[key] = photo
            return photo
        except Exception as e:
            print(f"Image load error: {e}")
            return None

    # ── Row builders ────────────────────────────────────────────────────────

    def _create_artist_row(self, rank, artist):
        row_bg = self.tertiary_bg
        frame = tk.Frame(
            self.artists_content, bg=row_bg,
            height=self.row_height - 6,
            highlightbackground=self.accent_color,
            highlightthickness=1,
        )
        frame.pack(fill=tk.X, padx=4, pady=2)
        frame.pack_propagate(False)

        rank_fg = self._contrast_fg(self.accent_color)
        tk.Label(
            frame,
            text=f"{rank:02d}",
            font=(FONT, 9, "bold"),
            bg=self.accent_color,
            fg=rank_fg,
            width=3,
            relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=(4, 0), pady=6)

        img = self.load_item_image(artist.get("image"))
        if img:
            lbl = tk.Label(frame, image=img, bg=row_bg, borderwidth=0)
            lbl.pack(side=tk.LEFT, padx=(4, 4), pady=4)
            self.item_images.append(img)

        info = tk.Frame(frame, bg=row_bg)
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=4)

        artist_url = artist.get("url", "#")
        artist_name_lbl = tk.Label(
            info,
            text=f"> {artist['name']}",
            font=(FONT, 8, "bold"),
            bg=row_bg,
            fg=self.fg_color,
            wraplength=230,
            justify=tk.LEFT,
            anchor=tk.W,
            cursor="hand2",
        )
        artist_name_lbl.pack(anchor=tk.W)
        artist_name_lbl.bind("<Button-1>", lambda e: webbrowser.open(artist_url) if artist_url != "#" else None)

        if artist.get("genres"):
            tk.Label(
                info,
                text=artist["genres"],
                font=(FONT, 6),
                bg=row_bg,
                fg=self.text_secondary,
                wraplength=230,
                justify=tk.LEFT,
                anchor=tk.W,
            ).pack(anchor=tk.W)

        pop = artist.get("popularity", 0)
        bar_frame = tk.Frame(frame, bg=row_bg)
        bar_frame.pack(side=tk.RIGHT, padx=6, pady=0, anchor=tk.CENTER)
        self._draw_pixel_bar(bar_frame, pop, width=24)

    def _create_track_row(self, rank, track):
        row_bg = self.tertiary_bg
        frame = tk.Frame(
            self.songs_content, bg=row_bg,
            height=self.row_height - 6,
            highlightbackground=self.accent_color,
            highlightthickness=1,
        )
        frame.pack(fill=tk.X, padx=4, pady=2)
        frame.pack_propagate(False)

        rank_fg = self._contrast_fg(self.accent_color)
        tk.Label(
            frame,
            text=f"{rank:02d}",
            font=(FONT, 9, "bold"),
            bg=self.accent_color,
            fg=rank_fg,
            width=3,
            relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=(4, 0), pady=6)

        img = self.load_item_image(track.get("image"))
        if img:
            lbl = tk.Label(frame, image=img, bg=row_bg, borderwidth=0)
            lbl.pack(side=tk.LEFT, padx=(4, 4), pady=4)
            self.item_images.append(img)

        info = tk.Frame(frame, bg=row_bg)
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=4)

        song_url = track.get("url", "#")
        song_name_lbl = tk.Label(
            info,
            text=f"> {track['name']}",
            font=(FONT, 8, "bold"),
            bg=row_bg,
            fg=self.fg_color,
            wraplength=220,
            justify=tk.LEFT,
            anchor=tk.W,
            cursor="hand2",
        )
        song_name_lbl.pack(anchor=tk.W)
        song_name_lbl.bind("<Button-1>", lambda e: webbrowser.open(song_url) if song_url != "#" else None)

        artist_url = track.get("artist_url", "#")
        artist_lbl = tk.Label(
            info,
            text=track["artist"],
            font=(FONT, 6),
            bg=row_bg,
            fg=self.text_secondary,
            wraplength=240,
            justify=tk.LEFT,
            anchor=tk.W,
            cursor="hand2",
        )
        artist_lbl.pack(anchor=tk.W)
        artist_lbl.bind("<Button-1>", lambda e: webbrowser.open(artist_url) if artist_url != "#" else None)

        pop = track.get("popularity", 0)
        bar_frame = tk.Frame(frame, bg=row_bg)
        bar_frame.pack(side=tk.RIGHT, padx=6, pady=0, anchor=tk.CENTER)
        self._draw_pixel_bar(bar_frame, pop, width=24)

    def _draw_pixel_bar(self, parent, value: int, width: int = 24):
        blocks  = 10
        filled  = max(0, min(blocks, round(value / 10)))
        block_h = 3
        block_w = width
        gap     = 1

        canvas = tk.Canvas(
            parent,
            width=block_w,
            height=blocks * (block_h + gap),
            bg=self.tertiary_bg,
            highlightthickness=0,
        )
        canvas.pack()

        for i in range(blocks):
            y_top = (blocks - 1 - i) * (block_h + gap)
            color = self.accent_color if i < filled else self.bg_color
            canvas.create_rectangle(
                0, y_top, block_w, y_top + block_h,
                fill=color, outline=self.secondary_bg,
            )


# ── Entry point ──────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    app  = SpotifyWidget(root)
    root.mainloop()
    try:
        if app._fisheye_overlay:
            app._fisheye_overlay.destroy()
    except Exception:
        pass
    app.save_settings()


if __name__ == "__main__":
    main()
