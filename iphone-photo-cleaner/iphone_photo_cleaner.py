#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           iPhone Photo Cleaner - Retro Edition               ║
║                   Est. 1995 Aesthetics                       ║
╚══════════════════════════════════════════════════════════════╝

A nostalgic Windows 95 / Mac OS 9 styled app to clean up old
iPhone photos. Because deleting files should feel like 1999.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from pathlib import Path
import threading
from io import BytesIO
from PIL import Image, ImageTk
import tempfile
import os
import logging
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import HEIC support
HEIC_AVAILABLE = False
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_AVAILABLE = True
    logger.info("HEIC support enabled via pillow-heif")
except ImportError:
    logger.warning("pillow-heif not installed - HEIC thumbnails will show as placeholders")
except Exception as e:
    logger.warning(f"pillow-heif failed to initialize: {e} - HEIC thumbnails will show as placeholders")

# Try to import pymobiledevice3
PYMOBILEDEVICE_AVAILABLE = False
try:
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.afc import AfcService
    PYMOBILEDEVICE_AVAILABLE = True
    logger.info("pymobiledevice3 loaded successfully")
except ImportError as e:
    logger.error(f"pymobiledevice3 not available: {e}")


class RetroColors:
    """Windows 95 / Classic Mac OS color palette"""
    # Window colors
    WINDOW_BG = "#c0c0c0"
    WINDOW_DARK = "#808080"
    WINDOW_LIGHT = "#ffffff"
    WINDOW_DARKER = "#404040"

    # Title bar
    TITLE_ACTIVE = "#000080"  # Classic navy blue
    TITLE_INACTIVE = "#808080"
    TITLE_TEXT = "#ffffff"

    # Button colors
    BUTTON_FACE = "#c0c0c0"
    BUTTON_HIGHLIGHT = "#ffffff"
    BUTTON_SHADOW = "#808080"
    BUTTON_DARK_SHADOW = "#404040"

    # Desktop teal (Windows 95 iconic color)
    DESKTOP_TEAL = "#008080"

    # Selection
    SELECTION_BG = "#000080"
    SELECTION_FG = "#ffffff"

    # Status bar
    STATUS_BG = "#c0c0c0"

    # Error/Warning
    ERROR_RED = "#ff0000"
    WARNING_YELLOW = "#ffff00"
    SUCCESS_GREEN = "#008000"


class RetroStyles:
    """Apply retro styling to widgets"""

    @staticmethod
    def configure_styles():
        style = ttk.Style()
        style.theme_use('clam')

        # Configure retro button
        style.configure(
            "Retro.TButton",
            background=RetroColors.BUTTON_FACE,
            foreground="black",
            borderwidth=2,
            relief="raised",
            padding=(10, 5),
            font=("MS Sans Serif", 10)
        )
        style.map("Retro.TButton",
            background=[("active", "#d4d4d4"), ("pressed", "#a0a0a0")],
            relief=[("pressed", "sunken")]
        )

        # Configure retro frame
        style.configure(
            "Retro.TFrame",
            background=RetroColors.WINDOW_BG,
            borderwidth=2,
            relief="raised"
        )

        # Sunken frame (for content areas)
        style.configure(
            "Sunken.TFrame",
            background=RetroColors.WINDOW_BG,
            borderwidth=2,
            relief="sunken"
        )

        # Configure labels
        style.configure(
            "Retro.TLabel",
            background=RetroColors.WINDOW_BG,
            foreground="black",
            font=("MS Sans Serif", 10)
        )

        # Title label
        style.configure(
            "Title.TLabel",
            background=RetroColors.TITLE_ACTIVE,
            foreground=RetroColors.TITLE_TEXT,
            font=("MS Sans Serif", 10, "bold"),
            padding=(5, 2)
        )

        # Configure progress bar
        style.configure(
            "Retro.Horizontal.TProgressbar",
            background=RetroColors.TITLE_ACTIVE,
            troughcolor=RetroColors.WINDOW_BG,
            borderwidth=2,
            relief="sunken"
        )

        # Configure scrollbar
        style.configure(
            "Retro.Vertical.TScrollbar",
            background=RetroColors.BUTTON_FACE,
            troughcolor=RetroColors.WINDOW_BG,
            borderwidth=2,
            arrowsize=15
        )


class RetroDatePicker(tk.Frame):
    """A Windows 95 style date picker"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=RetroColors.WINDOW_BG, **kwargs)

        self.selected_date = date(2025, 11, 25)

        # Month dropdown
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        # Create frame with 3D border effect
        picker_frame = tk.Frame(self, bg=RetroColors.WINDOW_BG)
        picker_frame.pack(pady=5)

        # Month
        tk.Label(picker_frame, text="Month:", bg=RetroColors.WINDOW_BG,
                 font=("MS Sans Serif", 9)).grid(row=0, column=0, padx=2)
        self.month_var = tk.StringVar(value="November")
        self.month_combo = ttk.Combobox(
            picker_frame,
            textvariable=self.month_var,
            values=months,
            width=12,
            state="readonly",
            font=("MS Sans Serif", 9)
        )
        self.month_combo.grid(row=0, column=1, padx=2)

        # Day
        tk.Label(picker_frame, text="Day:", bg=RetroColors.WINDOW_BG,
                 font=("MS Sans Serif", 9)).grid(row=0, column=2, padx=2)
        self.day_var = tk.StringVar(value="25")
        self.day_combo = ttk.Combobox(
            picker_frame,
            textvariable=self.day_var,
            values=[str(i) for i in range(1, 32)],
            width=4,
            state="readonly",
            font=("MS Sans Serif", 9)
        )
        self.day_combo.grid(row=0, column=3, padx=2)

        # Year
        tk.Label(picker_frame, text="Year:", bg=RetroColors.WINDOW_BG,
                 font=("MS Sans Serif", 9)).grid(row=0, column=4, padx=2)
        self.year_var = tk.StringVar(value="2025")
        self.year_combo = ttk.Combobox(
            picker_frame,
            textvariable=self.year_var,
            values=[str(i) for i in range(2015, 2027)],
            width=6,
            state="readonly",
            font=("MS Sans Serif", 9)
        )
        self.year_combo.grid(row=0, column=5, padx=2)

    def get_date(self):
        months = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        try:
            return date(
                int(self.year_var.get()),
                months[self.month_var.get()],
                int(self.day_var.get())
            )
        except (ValueError, KeyError):
            return None


class RetroImageGrid(tk.Frame):
    """A retro-styled image thumbnail grid"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=RetroColors.WINDOW_BG, **kwargs)

        # Create canvas with scrollbar
        self.canvas = tk.Canvas(
            self,
            bg="#ffffff",
            highlightthickness=2,
            highlightbackground=RetroColors.WINDOW_DARK,
            highlightcolor=RetroColors.WINDOW_DARK
        )

        self.scrollbar = tk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
            bg=RetroColors.BUTTON_FACE,
            troughcolor=RetroColors.WINDOW_BG,
            width=16
        )

        self.scrollable_frame = tk.Frame(self.canvas, bg="#ffffff")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Bind mousewheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.thumbnails = []
        self.photo_refs = []  # Keep references to prevent garbage collection
        self.selected = set()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def clear(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.thumbnails = []
        self.photo_refs = []
        self.selected = set()

    def add_thumbnail(self, image_data, filename, file_path, date_str):
        """Add a thumbnail with retro styling"""
        idx = len(self.thumbnails)
        row = idx // 4
        col = idx % 4

        # Create thumbnail frame with 3D effect
        thumb_frame = tk.Frame(
            self.scrollable_frame,
            bg=RetroColors.WINDOW_BG,
            bd=2,
            relief="raised",
            padx=5,
            pady=5
        )
        thumb_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # Determine file type for icon fallback
        is_video = filename.lower().endswith(('.mov', '.mp4', '.m4v'))
        is_heic = filename.lower().endswith(('.heic', '.heif'))

        # Try to create thumbnail from image data
        img_label = None
        try:
            if image_data and len(image_data) > 0:
                img = Image.open(BytesIO(image_data))
                img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.photo_refs.append(photo)

                img_label = tk.Label(
                    thumb_frame,
                    image=photo,
                    bg="#ffffff",
                    bd=2,
                    relief="sunken"
                )
                logger.debug(f"Loaded thumbnail for {filename}")
            else:
                raise ValueError("Empty image data")
        except Exception as e:
            logger.debug(f"Could not load thumbnail for {filename}: {e}")
            # Fallback: show appropriate retro file icon
            if is_video:
                icon_text = "🎬"
                icon_label = "VIDEO"
            elif is_heic and not HEIC_AVAILABLE:
                icon_text = "🖼️"
                icon_label = "HEIC"
            else:
                icon_text = "📷"
                icon_label = "PHOTO"

            img_label = tk.Label(
                thumb_frame,
                text=f"{icon_text}\n{icon_label}",
                font=("MS Sans Serif", 20),
                bg="#ffffff",
                width=8,
                height=4,
                bd=2,
                relief="sunken"
            )

        img_label.pack()

        # Filename label (truncated)
        name = filename[:15] + "..." if len(filename) > 15 else filename
        name_label = tk.Label(
            thumb_frame,
            text=name,
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 8),
            wraplength=100
        )
        name_label.pack()

        # Date label
        date_label = tk.Label(
            thumb_frame,
            text=date_str,
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 8),
            fg=RetroColors.WINDOW_DARK
        )
        date_label.pack()

        # Checkbox for selection
        var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(
            thumb_frame,
            text="Delete",
            variable=var,
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 8),
            activebackground=RetroColors.WINDOW_BG
        )
        chk.pack()

        self.thumbnails.append({
            "frame": thumb_frame,
            "path": file_path,
            "filename": filename,
            "selected": var
        })

    def get_selected(self):
        return [t for t in self.thumbnails if t["selected"].get()]

    def select_all(self):
        for t in self.thumbnails:
            t["selected"].set(True)

    def deselect_all(self):
        for t in self.thumbnails:
            t["selected"].set(False)


class RetroProgressDialog(tk.Toplevel):
    """A Windows 95 style progress dialog"""

    def __init__(self, parent, title="Progress"):
        super().__init__(parent)

        self.title(title)
        self.geometry("350x120")
        self.resizable(False, False)
        self.configure(bg=RetroColors.WINDOW_BG)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        # Main frame
        main_frame = tk.Frame(self, bg=RetroColors.WINDOW_BG, padx=15, pady=15)
        main_frame.pack(fill="both", expand=True)

        # Status label
        self.status_label = tk.Label(
            main_frame,
            text="Initializing...",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 9),
            anchor="w"
        )
        self.status_label.pack(fill="x", pady=(0, 10))

        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            style="Retro.Horizontal.TProgressbar",
            mode="determinate",
            length=300
        )
        self.progress.pack(fill="x", pady=(0, 10))

        # Count label
        self.count_label = tk.Label(
            main_frame,
            text="0 / 0",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 9)
        )
        self.count_label.pack()

    def update_progress(self, current, total, status=""):
        self.progress["maximum"] = total
        self.progress["value"] = current
        self.count_label.config(text=f"{current} / {total}")
        if status:
            self.status_label.config(text=status)
        self.update()


class iPhonePhotoCleaner(tk.Tk):
    """Main application window with retro styling"""

    def __init__(self):
        super().__init__()

        self.title("iPhone Photo Cleaner - Retro Edition")
        self.geometry("800x650")
        self.configure(bg=RetroColors.WINDOW_BG)

        # Apply retro styles
        RetroStyles.configure_styles()

        self.afc = None
        self.photos_data = []

        self._create_widgets()

    def _create_widgets(self):
        # ═══════════════════════════════════════════════════════
        # Title Bar (fake Windows 95 style)
        # ═══════════════════════════════════════════════════════
        title_bar = tk.Frame(self, bg=RetroColors.TITLE_ACTIVE, height=25)
        title_bar.pack(fill="x", padx=2, pady=(2, 0))
        title_bar.pack_propagate(False)

        # Icon and title
        tk.Label(
            title_bar,
            text="📱 iPhone Photo Cleaner",
            bg=RetroColors.TITLE_ACTIVE,
            fg=RetroColors.TITLE_TEXT,
            font=("MS Sans Serif", 10, "bold"),
            padx=5
        ).pack(side="left")

        # Fake window buttons
        btn_frame = tk.Frame(title_bar, bg=RetroColors.TITLE_ACTIVE)
        btn_frame.pack(side="right", padx=2)

        for symbol in ["─", "□", "✕"]:
            btn = tk.Button(
                btn_frame,
                text=symbol,
                font=("MS Sans Serif", 8),
                width=2,
                height=1,
                bd=2,
                relief="raised",
                bg=RetroColors.BUTTON_FACE
            )
            btn.pack(side="left", padx=1)

        # ═══════════════════════════════════════════════════════
        # Menu Bar
        # ═══════════════════════════════════════════════════════
        menu_bar = tk.Frame(self, bg=RetroColors.WINDOW_BG, bd=1, relief="raised")
        menu_bar.pack(fill="x", padx=2)

        for menu_text in ["File", "Edit", "View", "Help"]:
            btn = tk.Label(
                menu_bar,
                text=menu_text,
                bg=RetroColors.WINDOW_BG,
                font=("MS Sans Serif", 9),
                padx=8,
                pady=2
            )
            btn.pack(side="left")
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=RetroColors.SELECTION_BG, fg=RetroColors.SELECTION_FG))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=RetroColors.WINDOW_BG, fg="black"))

        # ═══════════════════════════════════════════════════════
        # Toolbar
        # ═══════════════════════════════════════════════════════
        toolbar = tk.Frame(self, bg=RetroColors.WINDOW_BG, bd=2, relief="groove")
        toolbar.pack(fill="x", padx=2, pady=2)

        # Connection status
        self.connection_frame = tk.Frame(toolbar, bg=RetroColors.WINDOW_BG)
        self.connection_frame.pack(side="left", padx=10, pady=5)

        self.status_icon = tk.Label(
            self.connection_frame,
            text="🔴",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 12)
        )
        self.status_icon.pack(side="left")

        self.connection_label = tk.Label(
            self.connection_frame,
            text="No iPhone Connected",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 9)
        )
        self.connection_label.pack(side="left", padx=5)

        # Connect button
        self.connect_btn = tk.Button(
            toolbar,
            text="🔌 Connect iPhone",
            font=("MS Sans Serif", 9),
            bd=2,
            relief="raised",
            bg=RetroColors.BUTTON_FACE,
            padx=10,
            command=self._connect_iphone
        )
        self.connect_btn.pack(side="left", padx=5, pady=5)

        # Separator
        tk.Frame(toolbar, width=2, bg=RetroColors.WINDOW_DARK).pack(side="left", fill="y", padx=10, pady=5)

        # Date picker section
        date_frame = tk.Frame(toolbar, bg=RetroColors.WINDOW_BG)
        date_frame.pack(side="left", padx=10)

        tk.Label(
            date_frame,
            text="Delete photos BEFORE:",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 9, "bold")
        ).pack(side="left")

        self.date_picker = RetroDatePicker(date_frame)
        self.date_picker.pack(side="left", padx=10)

        # Scan button
        self.scan_btn = tk.Button(
            toolbar,
            text="🔍 Scan Photos",
            font=("MS Sans Serif", 9),
            bd=2,
            relief="raised",
            bg=RetroColors.BUTTON_FACE,
            padx=10,
            command=self._scan_photos,
            state="disabled"
        )
        self.scan_btn.pack(side="left", padx=5, pady=5)

        # ═══════════════════════════════════════════════════════
        # Main Content Area
        # ═══════════════════════════════════════════════════════
        content_frame = tk.Frame(self, bg=RetroColors.WINDOW_BG)
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Info panel on left
        info_panel = tk.Frame(
            content_frame,
            bg=RetroColors.WINDOW_BG,
            bd=2,
            relief="groove",
            width=200
        )
        info_panel.pack(side="left", fill="y", padx=(0, 5))
        info_panel.pack_propagate(False)

        tk.Label(
            info_panel,
            text="📊 Statistics",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 10, "bold"),
            pady=10
        ).pack()

        # Stats frame
        stats_frame = tk.Frame(info_panel, bg=RetroColors.WINDOW_BG)
        stats_frame.pack(fill="x", padx=10)

        self.total_photos_label = tk.Label(
            stats_frame,
            text="Total Found: 0",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 9),
            anchor="w"
        )
        self.total_photos_label.pack(fill="x", pady=2)

        self.selected_label = tk.Label(
            stats_frame,
            text="Selected: 0",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 9),
            anchor="w"
        )
        self.selected_label.pack(fill="x", pady=2)

        self.size_label = tk.Label(
            stats_frame,
            text="Est. Size: 0 MB",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 9),
            anchor="w"
        )
        self.size_label.pack(fill="x", pady=2)

        # Separator
        tk.Frame(info_panel, height=2, bg=RetroColors.WINDOW_DARK).pack(fill="x", padx=10, pady=15)

        # Selection buttons
        tk.Label(
            info_panel,
            text="Selection",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 10, "bold")
        ).pack()

        tk.Button(
            info_panel,
            text="☑ Select All",
            font=("MS Sans Serif", 9),
            bd=2,
            relief="raised",
            bg=RetroColors.BUTTON_FACE,
            command=self._select_all
        ).pack(fill="x", padx=10, pady=5)

        tk.Button(
            info_panel,
            text="☐ Deselect All",
            font=("MS Sans Serif", 9),
            bd=2,
            relief="raised",
            bg=RetroColors.BUTTON_FACE,
            command=self._deselect_all
        ).pack(fill="x", padx=10, pady=5)

        # Separator
        tk.Frame(info_panel, height=2, bg=RetroColors.WINDOW_DARK).pack(fill="x", padx=10, pady=15)

        # Dry run checkbox
        self.dry_run_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            info_panel,
            text="🧪 Dry Run Mode",
            variable=self.dry_run_var,
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 9),
            activebackground=RetroColors.WINDOW_BG
        ).pack(padx=10, pady=5)

        tk.Label(
            info_panel,
            text="(Preview only,\nno actual deletion)",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 8),
            fg=RetroColors.WINDOW_DARK,
            justify="center"
        ).pack()

        # Delete button
        self.delete_btn = tk.Button(
            info_panel,
            text="🗑️ DELETE SELECTED",
            font=("MS Sans Serif", 10, "bold"),
            bd=3,
            relief="raised",
            bg="#ff6b6b",
            fg="white",
            activebackground="#ff4444",
            activeforeground="white",
            pady=10,
            command=self._delete_selected,
            state="disabled"
        )
        self.delete_btn.pack(fill="x", padx=10, pady=20)

        # Image grid
        grid_frame = tk.Frame(
            content_frame,
            bg=RetroColors.WINDOW_BG,
            bd=2,
            relief="sunken"
        )
        grid_frame.pack(side="left", fill="both", expand=True)

        self.image_grid = RetroImageGrid(grid_frame)
        self.image_grid.pack(fill="both", expand=True)

        # ═══════════════════════════════════════════════════════
        # Status Bar
        # ═══════════════════════════════════════════════════════
        status_bar = tk.Frame(self, bg=RetroColors.WINDOW_BG, bd=1, relief="sunken")
        status_bar.pack(fill="x", side="bottom", padx=2, pady=2)

        self.status_text = tk.Label(
            status_bar,
            text="Ready. Connect your iPhone to begin.",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 9),
            anchor="w",
            padx=5
        )
        self.status_text.pack(side="left", fill="x", expand=True)

        # Retro clock
        self.clock_label = tk.Label(
            status_bar,
            text="",
            bg=RetroColors.WINDOW_BG,
            font=("MS Sans Serif", 9),
            padx=10,
            bd=1,
            relief="sunken"
        )
        self.clock_label.pack(side="right")
        self._update_clock()

    def _update_clock(self):
        """Update the retro status bar clock"""
        current_time = datetime.now().strftime("%I:%M %p")
        self.clock_label.config(text=current_time)
        self.after(1000, self._update_clock)

    def _set_status(self, text, is_error=False):
        """Update status bar text"""
        self.status_text.config(
            text=text,
            fg=RetroColors.ERROR_RED if is_error else "black"
        )

    def _connect_iphone(self):
        """Connect to iPhone via USB"""
        if not PYMOBILEDEVICE_AVAILABLE:
            messagebox.showerror(
                "Missing Dependency",
                "pymobiledevice3 is not installed!\n\n"
                "Please run:\npip install pymobiledevice3 Pillow pillow-heif\n\n"
                "Then restart this application."
            )
            return

        self._set_status("Connecting to iPhone...")
        self.connect_btn.config(state="disabled")
        self.update()

        try:
            logger.info("Attempting to connect to iPhone via USB...")
            lockdown = create_using_usbmux()
            logger.info("Lockdown connection established")

            self.afc = AfcService(lockdown)
            logger.info("AFC service started")

            # Verify we can access DCIM
            try:
                dcim_contents = self.afc.listdir("/DCIM")
                logger.info(f"DCIM accessible, found {len(dcim_contents)} items")
            except Exception as dcim_error:
                logger.warning(f"Could not list DCIM: {dcim_error}")
                raise Exception(
                    "Connected to iPhone but cannot access photos.\n"
                    "Make sure the iPhone is unlocked and you've trusted this computer."
                )

            # Update UI
            self.status_icon.config(text="🟢")
            self.connection_label.config(text="iPhone Connected!")
            self.scan_btn.config(state="normal")
            self._set_status("iPhone connected successfully! Select a date and click Scan.")

            # Show HEIC warning if needed
            heic_warning = ""
            if not HEIC_AVAILABLE:
                heic_warning = (
                    "\n\n⚠️ Note: HEIC support not installed.\n"
                    "HEIC photos will show as placeholders but will still be deleted.\n"
                    "Run 'pip install pillow-heif' for thumbnail previews."
                )

            messagebox.showinfo(
                "Connected! 📱",
                f"iPhone connected successfully!\n\n"
                f"Now select a cutoff date and click 'Scan Photos' "
                f"to find photos older than that date.{heic_warning}"
            )

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            logger.error(traceback.format_exc())

            self.status_icon.config(text="🔴")
            self.connection_label.config(text="Connection Failed")
            self.connect_btn.config(state="normal")
            self._set_status(f"Error: {str(e)}", is_error=True)

            # Provide specific error guidance
            error_msg = str(e).lower()
            if "no device" in error_msg or "usbmux" in error_msg:
                hint = (
                    "No iPhone detected.\n\n"
                    "Make sure:\n"
                    "• iPhone is plugged in via USB cable\n"
                    "• You're using a data cable (not charge-only)\n"
                    "• The cable is fully connected"
                )
            elif "trust" in error_msg or "pair" in error_msg:
                hint = (
                    "iPhone not trusted.\n\n"
                    "On your iPhone:\n"
                    "1. Unlock the device\n"
                    "2. Tap 'Trust' when prompted\n"
                    "3. Enter your passcode if asked\n"
                    "4. Try connecting again"
                )
            elif "permission" in error_msg or "access" in error_msg:
                hint = (
                    "Permission denied.\n\n"
                    "Try running with sudo:\n"
                    "sudo python iphone_photo_cleaner.py\n\n"
                    "Or check System Preferences > Security & Privacy"
                )
            else:
                hint = (
                    f"Error: {str(e)}\n\n"
                    "Make sure:\n"
                    "• iPhone is plugged in via USB\n"
                    "• You tapped 'Trust' on the iPhone\n"
                    "• No other app (iTunes/Finder) is using the connection\n"
                    "• iPhone is unlocked"
                )

            messagebox.showerror("Connection Error", hint)

    def _scan_photos(self):
        """Scan iPhone for photos older than selected date"""
        cutoff_date = self.date_picker.get_date()
        if not cutoff_date:
            messagebox.showerror("Invalid Date", "Please select a valid date.")
            return

        if not self.afc:
            messagebox.showerror("Not Connected", "Please connect your iPhone first.")
            return

        logger.info(f"Starting scan for photos before {cutoff_date}")
        self._set_status(f"Scanning for photos before {cutoff_date}...")
        self.scan_btn.config(state="disabled")
        self.image_grid.clear()
        self.photos_data = []

        # Create progress dialog
        progress = RetroProgressDialog(self, "Scanning Photos...")

        def scan_thread():
            scan_errors = []
            try:
                # Get list of folders in DCIM
                logger.info("Listing DCIM folders...")
                dcim_folders = self.afc.listdir("/DCIM")
                dcim_folders = [f for f in dcim_folders if f not in [".", ".."]]
                logger.info(f"Found {len(dcim_folders)} DCIM folders")

                all_photos = []

                # Scan each folder
                for i, folder in enumerate(dcim_folders):
                    folder_path = f"/DCIM/{folder}"
                    try:
                        files = self.afc.listdir(folder_path)
                        for f in files:
                            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.heif', '.mov', '.mp4', '.m4v')):
                                all_photos.append(f"{folder_path}/{f}")
                    except Exception as folder_err:
                        logger.warning(f"Error scanning folder {folder}: {folder_err}")
                        scan_errors.append(f"Folder {folder}: {folder_err}")
                        continue

                    progress.update_progress(
                        i + 1,
                        len(dcim_folders),
                        f"Scanning {folder}..."
                    )

                logger.info(f"Found {len(all_photos)} total media files")

                # Check dates and filter
                progress.status_label.config(text="Checking file dates...")
                old_photos = []
                date_check_errors = 0

                for i, photo_path in enumerate(all_photos):
                    try:
                        stat = self.afc.stat(photo_path)
                        mtime = datetime.fromtimestamp(stat['st_mtime'])

                        if mtime.date() < cutoff_date:
                            old_photos.append({
                                "path": photo_path,
                                "filename": os.path.basename(photo_path),
                                "date": mtime,
                                "size": stat.get('st_size', 0)
                            })
                    except Exception as stat_err:
                        date_check_errors += 1
                        logger.debug(f"Could not stat {photo_path}: {stat_err}")
                        continue

                    if i % 10 == 0:
                        progress.update_progress(
                            i + 1,
                            len(all_photos),
                            f"Checking dates... Found {len(old_photos)} old photos"
                        )

                if date_check_errors > 0:
                    logger.warning(f"Could not check dates for {date_check_errors} files")

                logger.info(f"Found {len(old_photos)} photos before {cutoff_date}")

                # Load thumbnails (limit for performance)
                max_thumbnails = 100
                progress.status_label.config(text="Loading thumbnails...")

                for i, photo in enumerate(old_photos[:max_thumbnails]):
                    try:
                        # Only try to load thumbnails for images, not videos
                        if photo["filename"].lower().endswith(('.mov', '.mp4', '.m4v')):
                            # Videos get placeholder
                            self.after(0, lambda p=photo: self.image_grid.add_thumbnail(
                                b"",
                                p["filename"],
                                p["path"],
                                p["date"].strftime("%Y-%m-%d")
                            ))
                        else:
                            # Read image data
                            data = self.afc.get_file_contents(photo["path"])
                            self.after(0, lambda p=photo, d=data: self.image_grid.add_thumbnail(
                                d,
                                p["filename"],
                                p["path"],
                                p["date"].strftime("%Y-%m-%d")
                            ))
                    except Exception as thumb_err:
                        logger.debug(f"Could not load thumbnail for {photo['filename']}: {thumb_err}")
                        # Add placeholder if can't read
                        self.after(0, lambda p=photo: self.image_grid.add_thumbnail(
                            b"",
                            p["filename"],
                            p["path"],
                            p["date"].strftime("%Y-%m-%d")
                        ))

                    progress.update_progress(
                        i + 1,
                        min(len(old_photos), max_thumbnails),
                        f"Loading thumbnails..."
                    )

                self.photos_data = old_photos

                # Update UI
                total_size = sum(p.get("size", 0) for p in old_photos) / (1024 * 1024)

                self.after(0, lambda: self.total_photos_label.config(
                    text=f"Total Found: {len(old_photos)}"
                ))
                self.after(0, lambda: self.selected_label.config(
                    text=f"Selected: {len(old_photos)}"
                ))
                self.after(0, lambda: self.size_label.config(
                    text=f"Est. Size: {total_size:.1f} MB"
                ))
                self.after(0, lambda: self.delete_btn.config(state="normal" if old_photos else "disabled"))
                self.after(0, lambda: self.scan_btn.config(state="normal"))

                if old_photos:
                    self.after(0, lambda: self._set_status(
                        f"Found {len(old_photos)} photos before {cutoff_date}. "
                        f"Showing first {min(len(old_photos), max_thumbnails)} thumbnails."
                    ))
                else:
                    self.after(0, lambda: self._set_status(
                        f"No photos found before {cutoff_date}."
                    ))

                progress.destroy()

                # Show completion message
                if len(old_photos) > max_thumbnails:
                    self.after(0, lambda: messagebox.showinfo(
                        "Scan Complete",
                        f"Found {len(old_photos)} photos!\n\n"
                        f"Showing first {max_thumbnails} thumbnails for preview.\n"
                        f"All {len(old_photos)} will be deleted when you click Delete.\n\n"
                        f"Estimated space: {total_size:.1f} MB"
                    ))
                elif len(old_photos) == 0:
                    self.after(0, lambda: messagebox.showinfo(
                        "Scan Complete",
                        f"No photos found before {cutoff_date}.\n\n"
                        "Try selecting an earlier date."
                    ))

            except Exception as e:
                logger.error(f"Scan failed: {e}")
                logger.error(traceback.format_exc())
                progress.destroy()
                self.after(0, lambda: self.scan_btn.config(state="normal"))
                self.after(0, lambda: messagebox.showerror(
                    "Scan Error",
                    f"Error scanning photos:\n\n{str(e)}\n\n"
                    "The iPhone connection may have been lost.\n"
                    "Try reconnecting."
                ))
                self.after(0, lambda: self._set_status(f"Scan error: {e}", is_error=True))

        threading.Thread(target=scan_thread, daemon=True).start()

    def _select_all(self):
        self.image_grid.select_all()
        self.selected_label.config(text=f"Selected: {len(self.photos_data)}")

    def _deselect_all(self):
        self.image_grid.deselect_all()
        self.selected_label.config(text="Selected: 0")

    def _delete_selected(self):
        """Delete selected photos"""
        selected = self.image_grid.get_selected()

        if not selected and not self.photos_data:
            messagebox.showwarning("No Selection", "No photos selected for deletion.")
            return

        if not self.afc:
            messagebox.showerror("Not Connected", "iPhone connection lost. Please reconnect.")
            return

        dry_run = self.dry_run_var.get()
        total_to_delete = len(self.photos_data)
        total_size_mb = sum(p.get("size", 0) for p in self.photos_data) / (1024 * 1024)

        mode_text = "DRY RUN - " if dry_run else ""

        # More detailed confirmation
        if dry_run:
            confirm_msg = (
                f"[DRY RUN MODE]\n\n"
                f"This will SIMULATE deleting {total_to_delete} photos.\n"
                f"Estimated size: {total_size_mb:.1f} MB\n\n"
                f"No files will actually be deleted.\n\n"
                f"Continue with simulation?"
            )
        else:
            confirm_msg = (
                f"⚠️ WARNING - PERMANENT DELETION ⚠️\n\n"
                f"This will DELETE {total_to_delete} photos from your iPhone.\n"
                f"Estimated size: {total_size_mb:.1f} MB\n\n"
                f"THIS CANNOT BE UNDONE!\n\n"
                f"Make sure you have backed up these photos.\n\n"
                f"Are you absolutely sure?"
            )

        if not messagebox.askyesno(f"{mode_text}Confirm Deletion", confirm_msg):
            return

        # Double confirmation for actual deletion
        if not dry_run:
            if not messagebox.askyesno(
                "Final Confirmation",
                f"FINAL WARNING!\n\n"
                f"You are about to permanently delete {total_to_delete} photos.\n\n"
                f"Type 'DELETE' in your mind and click Yes to proceed."
            ):
                return

        logger.info(f"Starting {'dry run' if dry_run else 'deletion'} of {total_to_delete} photos")

        progress = RetroProgressDialog(
            self,
            "Dry Run..." if dry_run else "Deleting Photos..."
        )

        self.delete_btn.config(state="disabled")
        self.scan_btn.config(state="disabled")

        def delete_thread():
            deleted = 0
            errors = 0
            error_files = []

            for i, photo in enumerate(self.photos_data):
                try:
                    if not dry_run:
                        self.afc.rm(photo["path"])
                        logger.info(f"Deleted: {photo['path']}")
                    deleted += 1
                except Exception as e:
                    errors += 1
                    error_files.append(photo["filename"])
                    logger.error(f"Failed to delete {photo['path']}: {e}")

                progress.update_progress(
                    i + 1,
                    len(self.photos_data),
                    f"{'Simulating' if dry_run else 'Deleting'}: {photo['filename']}"
                )

            progress.destroy()

            # Build result message
            mode = "[DRY RUN] " if dry_run else ""

            if errors == 0:
                result_msg = (
                    f"{mode}{'Would delete' if dry_run else 'Successfully deleted'}: {deleted} photos\n\n"
                    f"{'Uncheck Dry Run mode to actually delete files.' if dry_run else 'All files removed from iPhone.'}"
                )
            else:
                result_msg = (
                    f"{mode}{'Would delete' if dry_run else 'Deleted'}: {deleted} photos\n"
                    f"Errors: {errors}\n\n"
                )
                if error_files[:5]:
                    result_msg += "Failed files:\n" + "\n".join(f"• {f}" for f in error_files[:5])
                    if len(error_files) > 5:
                        result_msg += f"\n...and {len(error_files) - 5} more"

            self.after(0, lambda: messagebox.showinfo(f"{mode}Complete!", result_msg))

            if not dry_run and deleted > 0:
                self.after(0, self.image_grid.clear)
                self.after(0, lambda: self.total_photos_label.config(text="Total Found: 0"))
                self.after(0, lambda: self.selected_label.config(text="Selected: 0"))
                self.after(0, lambda: self.size_label.config(text="Est. Size: 0 MB"))
                self.after(0, lambda: self.delete_btn.config(state="disabled"))
                self.photos_data = []

            self.after(0, lambda: self.scan_btn.config(state="normal"))
            self.after(0, lambda: self._set_status(
                f"{mode}{'Would have deleted' if dry_run else 'Deleted'} {deleted} photos. {errors} errors."
            ))

            logger.info(f"{'Dry run' if dry_run else 'Deletion'} complete: {deleted} deleted, {errors} errors")

        threading.Thread(target=delete_thread, daemon=True).start()


def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║   📱 iPhone Photo Cleaner - Retro Edition 📱              ║
    ║                                                            ║
    ║   A nostalgic way to clean up your camera roll            ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    if not PYMOBILEDEVICE_AVAILABLE:
        print("⚠️  Warning: pymobiledevice3 not installed!")
        print("   Run: pip install pymobiledevice3 Pillow")
        print()

    try:
        logger.info("Creating main window...")
        app = iPhonePhotoCleaner()
        logger.info("Starting main loop...")
        app.mainloop()
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        logger.error(traceback.format_exc())
        print(f"\n❌ Error starting application: {e}")
        print("\nThis might be a compatibility issue with your macOS version.")
        print("Try running: pip install --upgrade Pillow")
        raise


if __name__ == "__main__":
    main()
