"""
Spotify Dashboard Widget
Modern minimal desktop widget for displaying top Spotify artists and songs
"""

import tkinter as tk
from tkinter import ttk
import threading
import json
import os
import traceback

from spotify_auth import SpotifyAuthenticator
from spotify_api import SpotifyAPI


class SpotifyWidget:
    """Modern minimal Spotify Dashboard Widget"""

    # Color palettes
    PALETTES = {
        "dark": {
            "bg": "#0F0F0F",
            "secondary_bg": "#1a1a1a",
            "tertiary_bg": "#252525",
            "fg": "#FFFFFF",
            "accent": "#1DB954",
            "text_secondary": "#B3B3B3"
        },
        "purple": {
            "bg": "#0a0a0f",
            "secondary_bg": "#1a1517",
            "tertiary_bg": "#2d1f3a",
            "fg": "#FFFFFF",
            "accent": "#a855f7",
            "text_secondary": "#b4a8c4"
        },
        "blue": {
            "bg": "#0f0f1a",
            "secondary_bg": "#1a1f2e",
            "tertiary_bg": "#252f45",
            "fg": "#FFFFFF",
            "accent": "#3b82f6",
            "text_secondary": "#a3b8d6"
        },
        "pink": {
            "bg": "#14080a",
            "secondary_bg": "#2d1b22",
            "tertiary_bg": "#3f2833",
            "fg": "#FFFFFF",
            "accent": "#ec4899",
            "text_secondary": "#d4a5b2"
        },
        "teal": {
            "bg": "#081f1f",
            "secondary_bg": "#0f3838",
            "tertiary_bg": "#1a5555",
            "fg": "#FFFFFF",
            "accent": "#14b8a6",
            "text_secondary": "#7dd3c0"
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
        self.root.geometry("320x380")
        self.root.resizable(False, False)
        
        # Make window borderless but NOT overrideredirect yet
        # self.root.overrideredirect(True)
        
        # Make window draggable
        self.drag_data = {"x": 0, "y": 0}
        self.dragging_enabled = True
        
        # Settings
        self.config_file = "widget_config.json"
        self.settings = self.load_settings()
        
        # Initialize variables
        self.sp_client = None
        self.sp_api = None
        self.current_time_range = "medium_term"
        self.current_tab = "artists"
        self.current_palette = self.settings.get("palette", "dark")
        self.transparency = self.settings.get("transparency", 100)
        self.loading = False
        self.artists_data = []
        self.tracks_data = []
        self.settings_open = False
        self.demo_mode = False
        
        # Configure styles
        self.setup_styles()
        
        # Apply transparency
        self.apply_transparency()
        
        # Create UI first
        self.create_ui()
        
        # Make window draggable
        self.setup_drag()
        
        # Position window
        self.load_window_position()
        
        # Load demo data immediately
        self.demo_mode = True
        self.artists_data = self.DEMO_ARTISTS
        self.tracks_data = self.DEMO_TRACKS
        self.display_artists()
        self.display_songs()
        
        print("Widget loaded with demo data!")
        
        # Try to authenticate in background
        self.authenticate()

    def load_settings(self):
        """Load widget settings from config file"""
        default_settings = {
            "palette": "dark",
            "transparency": 100,
            "x": None,
            "y": None
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return default_settings
        
        return default_settings

    def save_settings(self):
        """Save widget settings to config file"""
        self.settings["palette"] = self.current_palette
        self.settings["transparency"] = self.transparency
        self.settings["x"] = self.root.winfo_x()
        self.settings["y"] = self.root.winfo_y()
        
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def load_window_position(self):
        """Load saved window position or default to bottom right"""
        self.root.update_idletasks()
        
        if self.settings.get("x") and self.settings.get("y"):
            self.root.geometry(f"+{self.settings['x']}+{self.settings['y']}")
        else:
            # Default to bottom right corner
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = screen_width - 340
            y = screen_height - 410
            self.root.geometry(f"+{x}+{y}")

    def apply_transparency(self):
        """Apply transparency based on slider value"""
        alpha = self.transparency / 100.0
        self.root.attributes('-alpha', alpha)

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
        
        self.root.configure(bg=self.bg_color)
        
        # Configure ttk style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background=self.bg_color, borderwidth=0)
        style.configure('TNotebook.Tab', padding=[12, 6])

    def create_ui(self):
        """Create the widget UI"""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Top control bar with tabs and time range
        control_frame = tk.Frame(main_frame, bg=self.secondary_bg)
        control_frame.pack(fill=tk.X, padx=0, pady=0)
        
        # Left frame for tabs
        tabs_frame = tk.Frame(control_frame, bg=self.secondary_bg)
        tabs_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=0, pady=0)
        
        # Create notebook (tabs) for Artists/Songs
        self.notebook = ttk.Notebook(tabs_frame)
        self.notebook.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=0, pady=0)
        
        # Artists tab
        artists_tab = tk.Frame(self.notebook, bg=self.secondary_bg)
        self.notebook.add(artists_tab, text="🎤")
        
        # Songs tab
        songs_tab = tk.Frame(self.notebook, bg=self.secondary_bg)
        self.notebook.add(songs_tab, text="🎵")
        
        # Bind tab change
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Right frame for time range and settings
        buttons_frame = tk.Frame(control_frame, bg=self.secondary_bg)
        buttons_frame.pack(side=tk.RIGHT, padx=6, pady=4)
        
        self.time_buttons = {}
        button_configs = [
            ("W", "short_term"),
            ("M", "medium_term"),
            ("6M", "long_term")
        ]
        
        for label, code in button_configs:
            is_selected = code == self.current_time_range
            btn = tk.Button(
                buttons_frame,
                text=label,
                font=("Segoe UI", 7, "bold"),
                bg=self.accent_color if is_selected else self.tertiary_bg,
                fg=self.bg_color if is_selected else self.fg_color,
                border=0,
                command=lambda c=code: self.change_time_range(c),
                relief=tk.FLAT,
                padx=5,
                pady=2,
                activebackground=self.accent_color,
                activeforeground=self.bg_color
            )
            btn.pack(side=tk.LEFT, padx=1)
            self.time_buttons[code] = btn
        
        # Settings button
        settings_btn = tk.Button(
            buttons_frame,
            text="⚙",
            font=("Arial", 8),
            bg=self.tertiary_bg,
            fg=self.text_secondary,
            border=0,
            command=self.toggle_settings,
            relief=tk.FLAT,
            padx=4,
            pady=2,
            activebackground=self.accent_color,
            activeforeground=self.bg_color
        )
        settings_btn.pack(side=tk.LEFT, padx=2)
        self.settings_btn = settings_btn
        
        # Content and settings container
        self.content_settings_frame = tk.Frame(main_frame, bg=self.bg_color)
        self.content_settings_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Create content frame (for artists/songs)
        self.content_frame = tk.Frame(self.content_settings_frame, bg=self.bg_color)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Create scrollable content for artists
        self.artists_canvas = tk.Canvas(
            self.content_frame,
            bg=self.bg_color,
            highlightthickness=0,
            borderwidth=0
        )
        self.artists_canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Scrollbar for artists
        artists_scroll = ttk.Scrollbar(
            self.content_frame,
            orient=tk.VERTICAL,
            command=self.artists_canvas.yview
        )
        artists_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.artists_canvas.config(yscrollcommand=artists_scroll.set)
        self.artists_content = tk.Frame(self.artists_canvas, bg=self.bg_color)
        self.artists_canvas.create_window((0, 0), window=self.artists_content, anchor=tk.NW, width=310)
        
        # Create scrollable content for songs
        self.songs_canvas = tk.Canvas(
            self.content_frame,
            bg=self.bg_color,
            highlightthickness=0,
            borderwidth=0
        )
        
        # Scrollbar for songs
        songs_scroll = ttk.Scrollbar(
            self.songs_canvas,
            orient=tk.VERTICAL,
            command=self.songs_canvas.yview
        )
        
        self.songs_canvas.config(yscrollcommand=songs_scroll.set)
        self.songs_content = tk.Frame(self.songs_canvas, bg=self.bg_color)
        self.songs_canvas.create_window((0, 0), window=self.songs_content, anchor=tk.NW, width=310)
        
        # Store canvases for switching
        self.canvases = {
            "artists": (self.artists_canvas, self.artists_content, artists_scroll),
            "songs": (self.songs_canvas, self.songs_content, songs_scroll)
        }
        
        # Bind mouse wheel
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Show artists canvas by default
        self.artists_canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        artists_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create settings frame (hidden by default)
        self.settings_frame = tk.Frame(self.content_settings_frame, bg=self.secondary_bg)

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
        self.settings_btn.config(bg=self.accent_color, fg=self.bg_color)
        
        # Hide content
        self.content_frame.pack_forget()
        
        # Clear settings frame
        for widget in self.settings_frame.winfo_children():
            widget.destroy()
        
        # Pack settings frame
        self.settings_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Title
        title_label = tk.Label(
            self.settings_frame,
            text="Settings",
            font=("Segoe UI", 10, "bold"),
            bg=self.secondary_bg,
            fg=self.accent_color
        )
        title_label.pack(pady=8)
        
        # Transparency section
        transparency_label = tk.Label(
            self.settings_frame,
            text="Opacity",
            font=("Segoe UI", 8),
            bg=self.secondary_bg,
            fg=self.text_secondary
        )
        transparency_label.pack(anchor=tk.W, padx=15, pady=(6, 2))
        
        transparency_frame = tk.Frame(self.settings_frame, bg=self.secondary_bg)
        transparency_frame.pack(fill=tk.X, padx=15, pady=(0, 8))
        
        self.transparency_slider = tk.Scale(
            transparency_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            bg=self.tertiary_bg,
            fg=self.accent_color,
            troughcolor=self.secondary_bg,
            highlightthickness=0,
            command=self.change_transparency,
            length=280
        )
        self.transparency_slider.set(self.transparency)
        self.transparency_slider.pack(fill=tk.X)
        
        # Color palettes section
        palette_label = tk.Label(
            self.settings_frame,
            text="Color Theme",
            font=("Segoe UI", 8),
            bg=self.secondary_bg,
            fg=self.text_secondary
        )
        palette_label.pack(anchor=tk.W, padx=15, pady=(6, 4))
        
        palettes_frame = tk.Frame(self.settings_frame, bg=self.secondary_bg)
        palettes_frame.pack(fill=tk.X, padx=15, pady=(0, 8))
        
        palette_names = ["dark", "purple", "blue", "pink", "teal"]
        for palette_name in palette_names:
            palette_btn = tk.Button(
                palettes_frame,
                text=palette_name.capitalize(),
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
        
        # Demo mode info
        demo_label = tk.Label(
            self.settings_frame,
            text=f"Mode: {'DEMO' if self.demo_mode else 'Live'}",
            font=("Segoe UI", 7),
            bg=self.secondary_bg,
            fg=self.accent_color if self.demo_mode else self.text_secondary
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
        self.settings_btn.config(bg=self.tertiary_bg, fg=self.text_secondary)
        
        # Hide settings frame
        self.settings_frame.pack_forget()
        
        # Show content frame
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Save settings
        self.save_settings()

    def change_transparency(self, value):
        """Change widget transparency"""
        self.transparency = int(value)
        self.apply_transparency()

    def change_palette(self, palette_name):
        """Change color palette"""
        self.current_palette = palette_name
        self.setup_styles()
        
        # Rebuild UI with new colors
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.create_ui()
        
        # Reopen settings
        self.open_settings()
        
        # Reload data with new colors
        if self.artists_data:
            self.display_artists()
        if self.tracks_data:
            self.display_songs()

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
        
        # Update button states
        for code, btn in self.time_buttons.items():
            if code == time_code:
                btn.config(bg=self.accent_color, fg=self.bg_color)
            else:
                btn.config(bg=self.tertiary_bg, fg=self.fg_color)
        
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
        for widget in self.songs_content.winfo_children():
            widget.destroy()
        
        if not self.tracks_data:
            return
        
        for idx, track in enumerate(self.tracks_data, 1):
            self.create_track_item(idx, track)
        
        self.songs_content.update_idletasks()
        self.songs_canvas.config(scrollregion=self.songs_canvas.bbox("all"))

    def create_artist_item(self, rank, artist):
        """Create artist item"""
        item_frame = tk.Frame(self.artists_content, bg=self.tertiary_bg)
        item_frame.pack(fill=tk.X, padx=6, pady=3)
        
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
        
        # Popularity bar
        popularity = artist['popularity']
        bar_frame = tk.Frame(info_frame, bg=self.secondary_bg, height=2)
        bar_frame.pack(fill=tk.X, pady=(2, 0))
        
        bar_fill = tk.Frame(
            bar_frame,
            bg=self.accent_color,
            height=2
        )
        bar_fill.pack(side=tk.LEFT, fill=tk.BOTH)
        bar_fill.config(width=int(230 * popularity / 100))

    def create_track_item(self, rank, track):
        """Create track item"""
        item_frame = tk.Frame(self.songs_content, bg=self.tertiary_bg)
        item_frame.pack(fill=tk.X, padx=6, pady=3)
        
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
            font=("Segoe UI", 6),
            bg=self.tertiary_bg,
            fg=self.text_secondary,
            wraplength=230,
            justify=tk.LEFT
        )
        artist_label.pack(anchor=tk.W)
        
        # Popularity bar
        popularity = track['popularity']
        bar_frame = tk.Frame(info_frame, bg=self.secondary_bg, height=2)
        bar_frame.pack(fill=tk.X, pady=(2, 0))
        
        bar_fill = tk.Frame(
            bar_frame,
            bg=self.accent_color,
            height=2
        )
        bar_fill.pack(side=tk.LEFT, fill=tk.BOTH)
        bar_fill.config(width=int(230 * popularity / 100))

    def on_tab_changed(self, event):
        """Handle tab change"""
        current_tab = self.notebook.index(self.notebook.select())
        self.current_tab = "artists" if current_tab == 0 else "songs"
        
        # Switch canvas visibility
        for canvas, content, scroll in self.canvases.values():
            canvas.pack_forget()
            scroll.pack_forget()
        
        if self.current_tab == "artists":
            canvas, content, scroll = self.canvases["artists"]
        else:
            canvas, content, scroll = self.canvases["songs"]
        
        canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)


def main():
    """Main entry point"""
    root = tk.Tk()
    root.configure(bg="#0F0F0F")
    root.resizable(False, False)
    
    print("Starting widget...")
    app = SpotifyWidget(root)
    print("Widget created, showing window...")
    root.deiconify()
    root.mainloop()
    
    # Save settings on close
    app.save_settings()


if __name__ == "__main__":
    main()
