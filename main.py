"""
Spotify Dashboard Widget
Modern minimal desktop widget for displaying top Spotify artists and songs
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import os

from spotify_auth import SpotifyAuthenticator
from spotify_api import SpotifyAPI


class SpotifyWidget:
    """Modern minimal Spotify Dashboard Widget"""

    def __init__(self, root):
        self.root = root
        self.root.title("Spotify Widget")
        self.root.geometry("380x450")
        self.root.resizable(False, False)
        
        # Make window borderless
        self.root.overrideredirect(True)
        
        # Make window draggable
        self.drag_data = {"x": 0, "y": 0}
        
        # Settings
        self.config_file = "widget_config.json"
        self.settings = self.load_settings()
        
        # Initialize variables
        self.sp_client = None
        self.sp_api = None
        self.current_time_range = "medium_term"
        self.current_tab = "artists"
        self.loading = False
        self.artists_data = []
        self.tracks_data = []
        
        # Configure styles
        self.setup_styles()
        
        # Apply transparency if enabled
        if self.settings.get("transparency", False):
            self.root.attributes('-alpha', 0.85)
        
        # Create UI
        self.create_ui()
        
        # Make window draggable
        self.setup_drag()
        
        # Position window
        self.load_window_position()
        
        # Try to authenticate
        self.authenticate()

    def load_settings(self):
        """Load widget settings from config file"""
        default_settings = {
            "transparency": False,
            "drop_shadow": False,
            "width": 380,
            "height": 450,
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
        self.settings["width"] = self.root.winfo_width()
        self.settings["height"] = self.root.winfo_height()
        self.settings["x"] = self.root.winfo_x()
        self.settings["y"] = self.root.winfo_y()
        
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def load_window_position(self):
        """Load saved window position or default to bottom right"""
        if self.settings.get("x") and self.settings.get("y"):
            self.root.geometry(f"+{self.settings['x']}+{self.settings['y']}")
        else:
            # Default to bottom right corner
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = screen_width - 400
            y = screen_height - 480
            self.root.geometry(f"+{x}+{y}")

    def setup_styles(self):
        """Setup custom styles for the widget"""
        # Colors (Spotify theme)
        self.bg_color = "#0F0F0F"
        self.secondary_bg = "#1a1a1a"
        self.tertiary_bg = "#252525"
        self.fg_color = "#FFFFFF"
        self.spotify_green = "#1DB954"
        self.text_secondary = "#B3B3B3"
        
        self.root.configure(bg=self.bg_color)
        
        # Configure ttk style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background=self.bg_color, borderwidth=0)
        style.configure('TNotebook.Tab', padding=[15, 8])

    def create_ui(self):
        """Create the widget UI"""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Top control bar with tabs and time range
        control_frame = tk.Frame(main_frame, bg=self.secondary_bg)
        control_frame.pack(fill=tk.X, padx=0, pady=0)
        
        # Create notebook (tabs) for Artists/Songs
        self.notebook = ttk.Notebook(control_frame)
        self.notebook.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=0, pady=0)
        
        # Artists tab
        artists_tab = tk.Frame(self.notebook, bg=self.secondary_bg)
        self.notebook.add(artists_tab, text="🎤")
        
        # Songs tab
        songs_tab = tk.Frame(self.notebook, bg=self.secondary_bg)
        self.notebook.add(songs_tab, text="🎵")
        
        # Bind tab change
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Time range and settings buttons frame
        buttons_frame = tk.Frame(control_frame, bg=self.secondary_bg)
        buttons_frame.pack(side=tk.RIGHT, padx=8, pady=6)
        
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
                bg=self.spotify_green if is_selected else self.tertiary_bg,
                fg=self.bg_color if is_selected else self.fg_color,
                border=0,
                command=lambda c=code: self.change_time_range(c),
                relief=tk.FLAT,
                padx=6,
                pady=3,
                activebackground=self.spotify_green,
                activeforeground=self.bg_color
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.time_buttons[code] = btn
        
        # Settings button
        settings_btn = tk.Button(
            buttons_frame,
            text="⚙",
            font=("Arial", 9),
            bg=self.tertiary_bg,
            fg=self.text_secondary,
            border=0,
            command=self.open_settings,
            relief=tk.FLAT,
            padx=6,
            pady=3,
            activebackground=self.spotify_green,
            activeforeground=self.bg_color
        )
        settings_btn.pack(side=tk.LEFT, padx=4)
        
        # Content frame for tabs
        content_frame = tk.Frame(main_frame, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Create scrollable content for artists
        self.artists_canvas = tk.Canvas(
            content_frame,
            bg=self.bg_color,
            highlightthickness=0,
            borderwidth=0
        )
        self.artists_canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Scrollbar for artists
        artists_scroll = ttk.Scrollbar(
            content_frame,
            orient=tk.VERTICAL,
            command=self.artists_canvas.yview
        )
        artists_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.artists_canvas.config(yscrollcommand=artists_scroll.set)
        self.artists_content = tk.Frame(self.artists_canvas, bg=self.bg_color)
        self.artists_canvas.create_window((0, 0), window=self.artists_content, anchor=tk.NW, width=365)
        
        # Create scrollable content for songs
        self.songs_canvas = tk.Canvas(
            content_frame,
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
        self.songs_canvas.create_window((0, 0), window=self.songs_content, anchor=tk.NW, width=365)
        
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
        
        # Status bar
        self.status_label = tk.Label(
            main_frame,
            text="Connecting...",
            font=("Segoe UI", 7),
            bg=self.secondary_bg,
            fg=self.text_secondary,
            justify=tk.LEFT
        )
        self.status_label.pack(fill=tk.X, padx=8, pady=4)

    def setup_drag(self):
        """Setup window dragging"""
        self.root.bind("<Button-1>", self.drag_start)
        self.root.bind("<B1-Motion>", self.drag_motion)
        self.root.bind("<ButtonRelease-1>", self.drag_stop)

    def drag_start(self, event):
        """Start dragging"""
        self.drag_data["x"] = event.x_root - self.root.winfo_x()
        self.drag_data["y"] = event.y_root - self.root.winfo_y()

    def drag_motion(self, event):
        """Handle dragging"""
        x = event.x_root - self.drag_data["x"]
        y = event.y_root - self.drag_data["y"]
        self.root.geometry(f"+{x}+{y}")

    def drag_stop(self, event):
        """Save position when drag stops"""
        self.save_settings()

    def open_settings(self):
        """Open settings window"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("300x200")
        settings_window.configure(bg=self.bg_color)
        settings_window.overrideredirect(True)
        
        # Center on widget
        widget_x = self.root.winfo_x()
        widget_y = self.root.winfo_y()
        settings_window.geometry(f"+{widget_x + 40}+{widget_y + 50}")
        
        # Main frame
        main_frame = tk.Frame(settings_window, bg=self.secondary_bg)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Settings",
            font=("Segoe UI", 12, "bold"),
            bg=self.secondary_bg,
            fg=self.spotify_green
        )
        title_label.pack(pady=10)
        
        # Transparency checkbox
        self.transparency_var = tk.BooleanVar(value=self.settings.get("transparency", False))
        transparency_check = tk.Checkbutton(
            main_frame,
            text="Transparent Background",
            font=("Segoe UI", 10),
            bg=self.secondary_bg,
            fg=self.fg_color,
            selectcolor=self.tertiary_bg,
            activebackground=self.secondary_bg,
            activeforeground=self.spotify_green,
            variable=self.transparency_var,
            command=self.toggle_transparency
        )
        transparency_check.pack(anchor=tk.W, padx=20, pady=5)
        
        # Drop shadow checkbox
        self.shadow_var = tk.BooleanVar(value=self.settings.get("drop_shadow", False))
        shadow_check = tk.Checkbutton(
            main_frame,
            text="Drop Shadow",
            font=("Segoe UI", 10),
            bg=self.secondary_bg,
            fg=self.fg_color,
            selectcolor=self.tertiary_bg,
            activebackground=self.secondary_bg,
            activeforeground=self.spotify_green,
            variable=self.shadow_var,
            command=self.toggle_shadow
        )
        shadow_check.pack(anchor=tk.W, padx=20, pady=5)
        
        # Close button
        close_btn = tk.Button(
            main_frame,
            text="Close",
            font=("Segoe UI", 9),
            bg=self.spotify_green,
            fg=self.bg_color,
            border=0,
            command=settings_window.destroy,
            relief=tk.FLAT,
            padx=20,
            pady=5
        )
        close_btn.pack(pady=10)

    def toggle_transparency(self):
        """Toggle widget transparency"""
        self.settings["transparency"] = self.transparency_var.get()
        if self.settings["transparency"]:
            self.root.attributes('-alpha', 0.85)
        else:
            self.root.attributes('-alpha', 1.0)
        self.save_settings()

    def toggle_shadow(self):
        """Toggle drop shadow (visual feedback for now)"""
        self.settings["drop_shadow"] = self.shadow_var.get()
        self.save_settings()
        if self.shadow_var.get():
            messagebox.showinfo("Info", "Drop shadow enabled (visual effect in future version)")

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if self.current_tab == "artists":
            self.artists_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        else:
            self.songs_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def authenticate(self):
        """Authenticate with Spotify API"""
        self.set_status("🔐 Authenticating...")
        threading.Thread(target=self._authenticate_thread, daemon=True).start()

    def _authenticate_thread(self):
        """Run authentication in background thread"""
        try:
            auth = SpotifyAuthenticator()
            self.sp_client = auth.get_spotify_client()
            self.sp_api = SpotifyAPI(self.sp_client)
            
            # Verify authentication
            user = self.sp_api.get_user_profile()
            self.set_status(f"✓ Logged in")
            
            # Load initial data
            self.load_data()
        except Exception as e:
            self.set_status(f"✗ Auth failed")
            self.root.after(2000, lambda: messagebox.showerror(
                "Authentication Error",
                f"Failed to authenticate:\n{str(e)}"
            ))

    def change_time_range(self, time_code):
        """Change time range and reload data"""
        self.current_time_range = time_code
        
        # Update button states
        for code, btn in self.time_buttons.items():
            if code == time_code:
                btn.config(bg=self.spotify_green, fg=self.bg_color)
            else:
                btn.config(bg=self.tertiary_bg, fg=self.fg_color)
        
        self.load_data()

    def load_data(self):
        """Load top artists and tracks"""
        if not self.sp_api:
            self.set_status("✗ Not authenticated")
            return
        
        self.loading = True
        self.set_status("📊 Loading...")
        threading.Thread(target=self._load_data_thread, daemon=True).start()

    def _load_data_thread(self):
        """Load data in background thread"""
        try:
            artists = self.sp_api.get_top_artists(self.current_time_range, limit=15)
            tracks = self.sp_api.get_top_tracks(self.current_time_range, limit=15)
            
            self.artists_data = artists
            self.tracks_data = tracks
            
            self.root.after(0, self.display_artists)
            self.root.after(0, self.display_songs)
            self.set_status("✓ Ready")
        except Exception as e:
            self.set_status(f"✗ Error")
        finally:
            self.loading = False

    def display_artists(self):
        """Display artists in tab"""
        # Clear
        for widget in self.artists_content.winfo_children():
            widget.destroy()
        
        if not self.artists_data:
            label = tk.Label(
                self.artists_content,
                text="No data available",
                bg=self.bg_color,
                fg=self.text_secondary,
                font=("Segoe UI", 9)
            )
            label.pack(pady=20)
            self.artists_canvas.config(scrollregion=self.artists_canvas.bbox("all"))
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
            label = tk.Label(
                self.songs_content,
                text="No data available",
                bg=self.bg_color,
                fg=self.text_secondary,
                font=("Segoe UI", 9)
            )
            label.pack(pady=20)
            self.songs_canvas.config(scrollregion=self.songs_canvas.bbox("all"))
            return
        
        for idx, track in enumerate(self.tracks_data, 1):
            self.create_track_item(idx, track)
        
        self.songs_content.update_idletasks()
        self.songs_canvas.config(scrollregion=self.songs_canvas.bbox("all"))

    def create_artist_item(self, rank, artist):
        """Create artist item"""
        item_frame = tk.Frame(self.artists_content, bg=self.tertiary_bg)
        item_frame.pack(fill=tk.X, padx=8, pady=4)
        
        # Rank circle
        rank_label = tk.Label(
            item_frame,
            text=f"{rank}",
            font=("Segoe UI", 9, "bold"),
            bg=self.spotify_green,
            fg=self.bg_color,
            width=2,
            height=1
        )
        rank_label.pack(side=tk.LEFT, padx=6, pady=6)
        
        # Info
        info_frame = tk.Frame(item_frame, bg=self.tertiary_bg)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        
        name_label = tk.Label(
            info_frame,
            text=artist['name'],
            font=("Segoe UI", 9, "bold"),
            bg=self.tertiary_bg,
            fg=self.fg_color,
            wraplength=280,
            justify=tk.LEFT
        )
        name_label.pack(anchor=tk.W)
        
        # Popularity bar
        popularity = artist['popularity']
        bar_frame = tk.Frame(info_frame, bg=self.secondary_bg, height=3)
        bar_frame.pack(fill=tk.X, pady=(3, 0))
        
        bar_fill = tk.Frame(
            bar_frame,
            bg=self.spotify_green,
            height=3
        )
        bar_fill.pack(side=tk.LEFT, fill=tk.BOTH)
        bar_fill.config(width=int(280 * popularity / 100))

    def create_track_item(self, rank, track):
        """Create track item"""
        item_frame = tk.Frame(self.songs_content, bg=self.tertiary_bg)
        item_frame.pack(fill=tk.X, padx=8, pady=4)
        
        # Rank circle
        rank_label = tk.Label(
            item_frame,
            text=f"{rank}",
            font=("Segoe UI", 9, "bold"),
            bg=self.spotify_green,
            fg=self.bg_color,
            width=2,
            height=1
        )
        rank_label.pack(side=tk.LEFT, padx=6, pady=6)
        
        # Info
        info_frame = tk.Frame(item_frame, bg=self.tertiary_bg)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        
        name_label = tk.Label(
            info_frame,
            text=track['name'],
            font=("Segoe UI", 9, "bold"),
            bg=self.tertiary_bg,
            fg=self.fg_color,
            wraplength=280,
            justify=tk.LEFT
        )
        name_label.pack(anchor=tk.W)
        
        artist_label = tk.Label(
            info_frame,
            text=track['artist'],
            font=("Segoe UI", 7),
            bg=self.tertiary_bg,
            fg=self.text_secondary,
            wraplength=280,
            justify=tk.LEFT
        )
        artist_label.pack(anchor=tk.W)
        
        # Popularity bar
        popularity = track['popularity']
        bar_frame = tk.Frame(info_frame, bg=self.secondary_bg, height=3)
        bar_frame.pack(fill=tk.X, pady=(3, 0))
        
        bar_fill = tk.Frame(
            bar_frame,
            bg=self.spotify_green,
            height=3
        )
        bar_fill.pack(side=tk.LEFT, fill=tk.BOTH)
        bar_fill.config(width=int(280 * popularity / 100))

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

    def set_status(self, message):
        """Update status"""
        self.status_label.config(text=message)


def main():
    """Main entry point"""
    root = tk.Tk()
    root.configure(bg="#0F0F0F")
    root.resizable(False, False)
    
    app = SpotifyWidget(root)
    root.mainloop()
    
    # Save settings on close
    app.save_settings()


if __name__ == "__main__":
    main()
