"""
Spotify Dashboard Widget
Modern minimal desktop widget for displaying top Spotify artists and songs
"""

import tkinter as tk
import threading
import json
import os
import traceback
import sys
from io import BytesIO

import requests
from PIL import Image, ImageTk
from spotify_auth import SpotifyAuthenticator
from spotify_api import SpotifyAPI


class SpotifyWidget:
    """Modern minimal Spotify Dashboard Widget"""

    # Color palettes
    PALETTES = {
        "cozy_earth": {
            "name": "Cozy Earth",
            "bg": "#CB997E",
            "secondary_bg": "#DDBEA9",
            "tertiary_bg": "#FFE8D6",
            "fg": "#1A1A1A",
            "accent": "#CB997E",
            "text_secondary": "#5C4B43"
        },
        "moonlit_ocean": {
            "name": "Moonlit Ocean",
            "bg": "#2B2D42",
            "secondary_bg": "#8D99AE",
            "tertiary_bg": "#EDF2F4",
            "fg": "#101218",
            "accent": "#2B2D42",
            "text_secondary": "#4C5668"
        },
        "sunny_peach": {
            "name": "Sunny Peach",
            "bg": "#ED6A5A",
            "secondary_bg": "#F4F1BB",
            "tertiary_bg": "#9BC1BC",
            "fg": "#111111",
            "accent": "#ED6A5A",
            "text_secondary": "#334A47"
        },
        "fiery_arctic": {
            "name": "Fiery Arctic",
            "bg": "#F6F7EB",
            "secondary_bg": "#E94F37",
            "tertiary_bg": "#393E41",
            "fg": "#FFFFFF",
            "accent": "#E94F37",
            "text_secondary": "#DDE2E4"
        }
    }

    # Demo data
    DEMO_ARTISTS = [
        {"name": "The Weeknd", "genres": "synth-pop, pop", "popularity": 92, "url": "#"},
        {"name": "Drake", "genres": "hip-hop, rap", "popularity": 88, "url": "#"},
        {"name": "Taylor Swift", "genres": "pop, country", "popularity": 95, "url": "#"},
        {"name": "Ariana Grande", "genres": "pop, r&b", "popularity": 90, "url": "#"},
        {"name": "Post Malone", "genres": "trap, hip-hop", "popularity": 85, "url": "#"},
        {"name": "Billie Eilish", "genres": "alternative, indie", "popularity": 88, "url": "#"},
        {"name": "Bad Bunny", "genres": "reggaeton, trap latino", "popularity": 92, "url": "#"},
        {"name": "Harry Styles", "genres": "pop, rock", "popularity": 86, "url": "#"},
        {"name": "Dua Lipa", "genres": "pop, dance", "popularity": 87, "url": "#"},
        {"name": "The Chainsmokers", "genres": "electronic, pop", "popularity": 80, "url": "#"},
        {"name": "Shawn Mendes", "genres": "pop, pop-rock", "popularity": 82, "url": "#"},
        {"name": "Khalid", "genres": "r&b, pop", "popularity": 79, "url": "#"},
        {"name": "Camila Cabello", "genres": "pop, latin", "popularity": 81, "url": "#"},
        {"name": "Alan Walker", "genres": "electronic, edm", "popularity": 75, "url": "#"},
        {"name": "Logic", "genres": "hip-hop, rap", "popularity": 77, "url": "#"},
    ]

    DEMO_TRACKS = [
        {"name": "Blinding Lights", "artist": "The Weeknd", "album": "After Hours", "popularity": 94, "url": "#", "duration_ms": 200040},
        {"name": "One Dance", "artist": "Drake ft. Wizkid & Kyla", "album": "Views", "popularity": 91, "url": "#", "duration_ms": 173293},
        {"name": "Levitating", "artist": "Dua Lipa ft. DaBaby", "album": "Future Nostalgia", "popularity": 93, "url": "#", "duration_ms": 203429},
        {"name": "Shape of You", "artist": "Ed Sheeran", "album": "÷", "popularity": 95, "url": "#", "duration_ms": 233613},
        {"name": "Peaches", "artist": "Justin Bieber ft. Daniel Caesar", "album": "Justice", "popularity": 89, "url": "#", "duration_ms": 198973},
        {"name": "Anti-Hero", "artist": "Taylor Swift", "album": "Midnights", "popularity": 96, "url": "#", "duration_ms": 229080},
        {"name": "As It Was", "artist": "Harry Styles", "album": "Harry's House", "popularity": 92, "url": "#", "duration_ms": 169213},
        {"name": "Heat Waves", "artist": "Glass Animals", "album": "Dreamland", "popularity": 88, "url": "#", "duration_ms": 239426},
        {"name": "Sunroof", "artist": "Nicky Youre", "album": "Sunroof", "popularity": 87, "url": "#", "duration_ms": 180160},
        {"name": "Running Up That Hill", "artist": "Kate Bush", "album": "Stranger Things Vol. 1", "popularity": 90, "url": "#", "duration_ms": 326400},
        {"name": "Flowers", "artist": "Miley Cyrus", "album": "Endless Summer Vacation", "popularity": 91, "url": "#", "duration_ms": 200040},
        {"name": "Industry Baby", "artist": "Lil Nas X & Jack Harlow", "album": "Montero", "popularity": 85, "url": "#", "duration_ms": 218973},
        {"name": "Vampire", "artist": "Olivia Rodrigo", "album": "GUTS", "popularity": 84, "url": "#", "duration_ms": 243080},
        {"name": "Dance the Night", "artist": "Dua Lipa", "album": "Barbie The Album", "popularity": 89, "url": "#", "duration_ms": 191160},
        {"name": "Cruel Summer", "artist": "Taylor Swift", "album": "Lover", "popularity": 92, "url": "#", "duration_ms": 169293},
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("Spotify Widget")
        self.widget_width = 390
        self.widget_height = 390
        self.visible_rows = 5
        self.row_height = 58
        self.control_height = 58
        self.content_height = self.widget_height - self.control_height
        self.root.geometry(f"{self.widget_width}x{self.widget_height}")
        self.root.resizable(False, False)
        
        # Remove the operating system window border for widget-style display.
        self.root.overrideredirect(True)
        
        # Make window draggable
        self.drag_data = {"x": 0, "y": 0}
        self.dragging_enabled = True
        
        # Settings
        self.config_file = "widget_config.json"
        self.settings = self.load_settings()
        
        # Initialize variables FIRST
        self.sp_client = None
        self.sp_api = None
        self.current_time_range = "medium_term"
        self.current_tab = "artists"
        self.drag_data = {"x": 0, "y": 0}
        self.dragging_enabled = True
        self.loading = False
        self.artists_data = []
        self.tracks_data = []
        self.settings_open = False
        self.demo_mode = False
        self.image_cache = {}
        self.item_images = []
        
        # Settings
        self.config_file = "widget_config.json"
        self.settings = self.load_settings()
        
        self.current_palette = self.settings.get("palette", "cozy_earth")
        if self.current_palette not in self.PALETTES:
            self.current_palette = "cozy_earth"
        # Configure styles BEFORE creating widgets
        self.setup_styles()
        
        # Set window properties
        self.root.geometry(f"{self.widget_width}x{self.widget_height}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.panel_bg)
        self.enable_rounded_corners()
        
        # Create UI
        print("Creating UI...")
        self.create_ui()
        
        # Make window draggable
        self.setup_drag()
        
        # Position and show window
        self.load_window_position()
        self.root.after(50, self.load_window_position)
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        
        # Apply saved colors
        self.apply_theme_colors()
        
        # Load demo data immediately
        print("Loading demo data...")
        self.demo_mode = True
        self.artists_data = self.DEMO_ARTISTS
        self.tracks_data = self.DEMO_TRACKS
        self.display_artists()
        self.display_songs()
        
        print("Widget loaded with demo data!")
        
        # Try to authenticate in background
        # self.authenticate()

    def enable_rounded_corners(self):
        """Clip the borderless window into a rounded square panel."""
        if sys.platform != "win32":
            return

        try:
            import ctypes

            # Force DWM compositing on the overrideredirect window.
            # Without this, pixels outside the rounded region render as solid
            # black instead of showing the desktop behind the widget.
            self.root.wm_attributes('-alpha', 0.99)

            # Ensure the window handle is ready before making Win32 calls.
            self.root.update_idletasks()
            hwnd = self.root.winfo_id()
            if not hwnd:
                return

            corner_radius = 24

            # Apply the rounded clip region.  Create a fresh region handle for
            # each HWND — SetWindowRgn transfers ownership of the handle so
            # reusing the same one for a second call would pass a dangling ptr.
            for h in (hwnd, ctypes.windll.user32.GetParent(hwnd)):
                if h:
                    rgn = ctypes.windll.gdi32.CreateRoundRectRgn(
                        0,
                        0,
                        self.widget_width + 1,
                        self.widget_height + 1,
                        corner_radius,
                        corner_radius,
                    )
                    ctypes.windll.user32.SetWindowRgn(h, rgn, True)

            # Windows 11+: also request native rounded corners via DWM so the
            # drop shadow and anti-aliasing look correct at the edges.
            try:
                DWMWA_WINDOW_CORNER_PREFERENCE = 33
                DWMWCP_ROUND = 2
                preference = ctypes.c_int(DWMWCP_ROUND)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_WINDOW_CORNER_PREFERENCE,
                    ctypes.byref(preference),
                    ctypes.sizeof(preference),
                )
            except Exception:
                pass

        except Exception:
            pass

    def load_settings(self):
        """Load widget settings from config file"""
        default_settings = {
            "palette": "cozy_earth",
            "x": None,
            "y": None
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_settings = json.load(f)
                    default_settings.update(loaded_settings)

                    return default_settings
            except:
                return default_settings
        
        return default_settings

    def save_settings(self):
        """Save widget settings to config file"""
        self.settings["palette"] = self.current_palette
        self.settings["x"] = self.root.winfo_x()
        self.settings["y"] = self.root.winfo_y()
        
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def load_window_position(self):
        """Default to bottom right of the screen."""
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - self.widget_width - 24
        y = screen_height - self.widget_height - 64
        self.root.geometry(f"{self.widget_width}x{self.widget_height}+{x}+{y}")

    def apply_theme_colors(self):
        """Refresh widget colors after settings change."""
        self.setup_styles()
        self.update_background_colors()

    def setup_styles(self):
        """Setup custom styles for the widget"""
        # Get current palette colors
        self.palette = self.PALETTES[self.current_palette]
        self.bg_color = self.palette["bg"]
        self.secondary_bg = self.palette["secondary_bg"]
        self.tertiary_bg = self.palette["tertiary_bg"]
        self.fg_color = self.palette["fg"]
        self.accent_color = self.palette["accent"]
        self.text_secondary = self.palette["text_secondary"]
        self.panel_bg = self.bg_color

    def update_background_colors(self):
        for attr in ("main_frame", "content_settings_frame"):
            if hasattr(self, attr):
                getattr(self, attr).configure(bg=self.panel_bg)

        for attr in ("content_frame", "artists_canvas", "artists_content", "songs_canvas", "songs_content"):
            if hasattr(self, attr):
                getattr(self, attr).configure(bg=self.tertiary_bg)

    def create_ui(self):
        """Create the widget UI"""
        main_frame = tk.Frame(self.root, bg=self.panel_bg)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.main_frame = main_frame

        self.content_settings_frame = tk.Frame(main_frame, bg=self.panel_bg)
        self.content_settings_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.content_frame = tk.Frame(self.content_settings_frame, bg=self.tertiary_bg)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.content_frame.configure(height=self.content_height)
        self.content_frame.pack_propagate(False)

        self.control_frame = tk.Frame(main_frame, bg=self.secondary_bg)
        self.control_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=0)

        buttons_frame = tk.Frame(self.control_frame, bg=self.secondary_bg)
        buttons_frame.pack(fill=tk.X, padx=6, pady=6)

        self.tab_buttons = {}
        for label, tab_name in [("Artists", "artists"), ("Songs", "songs")]:
            btn = self.create_control_button(
                buttons_frame,
                label,
                lambda name=tab_name: self.change_tab(name)
            )
            btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
            self.tab_buttons[tab_name] = btn

        self.time_buttons = {}
        for label, code in [("Week", "short_term"), ("Month", "medium_term"), ("6M", "long_term")]:
            btn = self.create_control_button(
                buttons_frame,
                label,
                lambda c=code: self.change_time_range(c)
            )
            btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
            self.time_buttons[code] = btn

        settings_btn = self.create_control_button(
            buttons_frame,
            "Settings",
            self.toggle_settings
        )
        settings_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.settings_btn = settings_btn
        self.update_control_states()

        self.artists_canvas = tk.Canvas(
            self.content_frame,
            bg=self.tertiary_bg,
            highlightthickness=0,
            borderwidth=0,
            relief="flat"
        )
        self.artists_canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.artists_content = tk.Frame(self.artists_canvas, bg=self.tertiary_bg)
        self.artists_canvas.create_window((0, 0), window=self.artists_content, anchor=tk.NW, width=self.widget_width)

        self.songs_canvas = tk.Canvas(
            self.content_frame,
            bg=self.tertiary_bg,
            highlightthickness=0,
            borderwidth=0,
            relief="flat"
        )

        self.songs_content = tk.Frame(self.songs_canvas, bg=self.tertiary_bg)
        self.songs_canvas.create_window((0, 0), window=self.songs_content, anchor=tk.NW, width=self.widget_width)

        self.canvases = {
            "artists": (self.artists_canvas, self.artists_content),
            "songs": (self.songs_canvas, self.songs_content)
        }

        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.artists_canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.settings_frame = tk.Frame(self.content_settings_frame, bg=self.secondary_bg)

    def create_control_button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 7, "bold"),
            bg=self.tertiary_bg,
            fg=self.fg_color,
            border=1,
            command=command,
            relief=tk.RAISED,
            padx=4,
            pady=6,
            activebackground=self.tertiary_bg,
            activeforeground=self.fg_color
        )

    def update_control_states(self):
        if not hasattr(self, "tab_buttons"):
            return

        for tab, btn in self.tab_buttons.items():
            btn.config(relief=tk.SUNKEN if tab == self.current_tab else tk.RAISED)

        for code, btn in self.time_buttons.items():
            btn.config(relief=tk.SUNKEN if code == self.current_time_range else tk.RAISED)

    def toggle_settings(self):
        """Toggle settings panel"""
        if self.settings_open:
            self.close_settings()
        else:
            self.open_settings()

    def open_settings(self):
        """Open settings panel"""
        self.settings_open = True
        self.dragging_enabled = False
        self.settings_btn.config(relief=tk.SUNKEN)
        
        # Hide content
        self.content_frame.pack_forget()
        
        # Clear settings frame
        for widget in self.settings_frame.winfo_children():
            widget.destroy()
        
        # Pack settings frame
        self.settings_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Title — use fg_color so it's always legible against secondary_bg,
        # even in themes where accent_color == secondary_bg (e.g. fiery_arctic).
        title_label = tk.Label(
            self.settings_frame,
            text="Settings",
            font=("Segoe UI", 10, "bold"),
            bg=self.secondary_bg,
            fg=self.fg_color,
        )
        title_label.pack(pady=8)
        
        # Color palettes section
        palette_label = tk.Label(
            self.settings_frame,
            text="Color Theme",
            font=("Segoe UI", 8),
            bg=self.secondary_bg,
            fg=self.fg_color,
        )
        palette_label.pack(anchor=tk.W, padx=15, pady=(6, 4))
        
        palettes_frame = tk.Frame(self.settings_frame, bg=self.secondary_bg)
        palettes_frame.pack(fill=tk.X, padx=15, pady=(0, 8))
        
        palette_names = ["cozy_earth", "moonlit_ocean", "sunny_peach", "fiery_arctic"]
        for palette_name in palette_names:
            palette_btn = tk.Button(
                palettes_frame,
                text=self.PALETTES[palette_name]["name"],
                font=("Segoe UI", 7),
                bg=self.accent_color if palette_name == self.current_palette else self.tertiary_bg,
                fg=self.bg_color if palette_name == self.current_palette else self.fg_color,
                border=0,
                command=lambda p=palette_name: self.change_palette(p),
                relief=tk.FLAT,
                padx=8,
                pady=3,
                activebackground=self.accent_color,
                activeforeground=self.bg_color
            )
            palette_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # Demo mode info — same fix: fg_color guarantees contrast on secondary_bg.
        demo_label = tk.Label(
            self.settings_frame,
            text=f"Mode: {'DEMO' if self.demo_mode else 'Live'}",
            font=("Segoe UI", 7),
            bg=self.secondary_bg,
            fg=self.fg_color,
        )
        demo_label.pack(pady=(8, 0))
        
        # Close button
        close_btn = tk.Button(
            self.settings_frame,
            text="Close",
            font=("Segoe UI", 8, "bold"),
            bg=self.accent_color,
            fg=self.bg_color,
            border=0,
            command=self.close_settings,
            relief=tk.FLAT,
            padx=20,
            pady=6
        )
        close_btn.pack(pady=6)

    def close_settings(self):
        """Close settings panel"""
        self.settings_open = False
        self.dragging_enabled = True
        self.settings_btn.config(relief=tk.RAISED)
        
        # Hide settings frame
        self.settings_frame.pack_forget()
        
        # Show content frame
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Save settings
        self.save_settings()
        self.update_control_states()

    def change_palette(self, palette_name):
        """Change color palette"""
        reopen_settings = self.settings_open
        self.current_palette = palette_name
        self.setup_styles()
        
        # Rebuild UI with new colors
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.root.configure(bg=self.panel_bg)
        self.create_ui()

        if self.artists_data:
            self.display_artists()
        if self.tracks_data:
            self.display_songs()

        if reopen_settings:
            self.open_settings()

    def setup_drag(self):
        """Setup window dragging"""
        self.root.bind("<Button-1>", self.drag_start)
        self.root.bind("<B1-Motion>", self.drag_motion)
        self.root.bind("<ButtonRelease-1>", self.drag_stop)

    def drag_start(self, event):
        """Start dragging"""
        if self.dragging_enabled:
            self.drag_data["x"] = event.x_root - self.root.winfo_x()
            self.drag_data["y"] = event.y_root - self.root.winfo_y()

    def drag_motion(self, event):
        """Handle dragging"""
        if self.dragging_enabled:
            x = event.x_root - self.drag_data["x"]
            y = event.y_root - self.drag_data["y"]
            self.root.geometry(f"+{x}+{y}")

    def drag_stop(self, event):
        """Save position when drag stops"""
        if self.dragging_enabled:
            self.save_settings()

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if self.settings_open:
            return
        
        if self.current_tab == "artists":
            self.artists_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        else:
            self.songs_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def authenticate(self):
        """Authenticate with Spotify API"""
        threading.Thread(target=self._authenticate_thread, daemon=True).start()

    def _authenticate_thread(self):
        """Run authentication in background thread"""
        try:
            auth = SpotifyAuthenticator()
            self.sp_client = auth.get_spotify_client()
            self.sp_api = SpotifyAPI(self.sp_client)
            
            # Load initial data
            self.load_data()
        except Exception as e:
            print(f"Auth error (using demo mode): {e}")

    def change_time_range(self, time_code):
        """Change time range and reload data"""
        self.current_time_range = time_code
        self.update_control_states()
        
        if not self.demo_mode:
            self.load_data()

    def load_data(self):
        """Load top artists and tracks"""
        if not self.sp_api:
            return
        
        self.loading = True
        threading.Thread(target=self._load_data_thread, daemon=True).start()

    def _load_data_thread(self):
        """Load data in background thread"""
        try:
            artists = self.sp_api.get_top_artists(self.current_time_range, limit=15)
            tracks = self.sp_api.get_top_tracks(self.current_time_range, limit=15)
            
            if artists and tracks:
                self.artists_data = artists
                self.tracks_data = tracks
                self.demo_mode = False
                
                self.root.after(0, self.display_artists)
                self.root.after(0, self.display_songs)
                print("Switched to live data!")
        except Exception as e:
            print(f"Data load error (staying in demo mode): {e}")
        finally:
            self.loading = False

    def display_artists(self):
        """Display artists in tab"""
        # Clear
        self.item_images = []
        for widget in self.artists_content.winfo_children():
            widget.destroy()
        
        if not self.artists_data:
            return
        
        for idx, artist in enumerate(self.artists_data, 1):
            self.create_artist_item(idx, artist)
        
        self.artists_content.update_idletasks()
        self.artists_canvas.config(scrollregion=self.artists_canvas.bbox("all"))

    def display_songs(self):
        """Display songs in tab"""
        # Clear
        self.item_images = []
        for widget in self.songs_content.winfo_children():
            widget.destroy()
        
        if not self.tracks_data:
            return
        
        for idx, track in enumerate(self.tracks_data, 1):
            self.create_track_item(idx, track)
        
        self.songs_content.update_idletasks()
        self.songs_canvas.config(scrollregion=self.songs_canvas.bbox("all"))

    def load_item_image(self, image_url, size=38):
        """Load and cache Spotify artist/album images for live data rows."""
        if not image_url:
            return None

        cache_key = (image_url, size)
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        try:
            response = requests.get(image_url, timeout=5)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGB")
            image.thumbnail((size, size), Image.LANCZOS)

            square = Image.new("RGB", (size, size), self.tertiary_bg)
            offset = ((size - image.width) // 2, (size - image.height) // 2)
            square.paste(image, offset)

            photo = ImageTk.PhotoImage(square)
            self.image_cache[cache_key] = photo
            return photo
        except Exception as e:
            print(f"Image load error: {e}")
            return None

    def create_artist_item(self, rank, artist):
        """Create artist item"""
        item_frame = tk.Frame(self.artists_content, bg=self.tertiary_bg, height=self.row_height - 6)
        item_frame.pack(fill=tk.X, padx=6, pady=3)
        item_frame.pack_propagate(False)
        
        # Rank circle
        rank_label = tk.Label(
            item_frame,
            text=f"{rank}",
            font=("Segoe UI", 8, "bold"),
            bg=self.accent_color,
            fg=self.bg_color,
            width=2,
            height=1
        )
        rank_label.pack(side=tk.LEFT, padx=5, pady=5)

        artist_image = self.load_item_image(artist.get("image"))
        if artist_image:
            image_label = tk.Label(
                item_frame,
                image=artist_image,
                bg=self.tertiary_bg,
                borderwidth=0
            )
            image_label.pack(side=tk.LEFT, padx=(0, 6), pady=5)
            self.item_images.append(artist_image)
        
        # Info
        info_frame = tk.Frame(item_frame, bg=self.tertiary_bg)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        name_label = tk.Label(
            info_frame,
            text=artist['name'],
            font=("Segoe UI", 8, "bold"),
            bg=self.tertiary_bg,
            fg=self.fg_color,
            wraplength=230,
            justify=tk.LEFT
        )
        name_label.pack(anchor=tk.W)

    def create_track_item(self, rank, track):
        """Create track item"""
        item_frame = tk.Frame(self.songs_content, bg=self.tertiary_bg, height=self.row_height - 6)
        item_frame.pack(fill=tk.X, padx=6, pady=3)
        item_frame.pack_propagate(False)
        
        # Rank circle
        rank_label = tk.Label(
            item_frame,
            text=f"{rank}",
            font=("Segoe UI", 8, "bold"),
            bg=self.accent_color,
            fg=self.bg_color,
            width=2,
            height=1
        )
        rank_label.pack(side=tk.LEFT, padx=5, pady=5)

        album_image = self.load_item_image(track.get("image"))
        if album_image:
            image_label = tk.Label(
                item_frame,
                image=album_image,
                bg=self.tertiary_bg,
                borderwidth=0
            )
            image_label.pack(side=tk.LEFT, padx=(0, 6), pady=5)
            self.item_images.append(album_image)
        
        # Info
        info_frame = tk.Frame(item_frame, bg=self.tertiary_bg)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        name_label = tk.Label(
            info_frame,
            text=track['name'],
            font=("Segoe UI", 8, "bold"),
            bg=self.tertiary_bg,
            fg=self.fg_color,
            wraplength=230,
            justify=tk.LEFT
        )
        name_label.pack(anchor=tk.W)
        
        artist_label = tk.Label(
            info_frame,
            text=track['artist'],
            font=("Segoe UI", 7),
            bg=self.tertiary_bg,
            fg=self.text_secondary,
            wraplength=260,
            justify=tk.LEFT
        )
        artist_label.pack(anchor=tk.W)

    def change_tab(self, tab_name):
        """Switch between artist and song lists."""
        self.current_tab = tab_name
        self.update_control_states()
        
        # Switch canvas visibility
        for canvas, content in self.canvases.values():
            canvas.pack_forget()
        
        if self.current_tab == "artists":
            canvas, content = self.canvases["artists"]
        else:
            canvas, content = self.canvases["songs"]
        
        canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)


def main():
    """Main entry point"""
    print("Creating root window...")
    root = tk.Tk()
    
    print("Creating SpotifyWidget...")
    app = SpotifyWidget(root)
    
    print("Starting mainloop...")
    root.mainloop()
    
    # Save settings on close
    app.save_settings()


if __name__ == "__main__":
    main()