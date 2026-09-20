import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import requests
import json
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
matplotlib.use("TkAgg")
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
import io
import base64
import os
import math

# Load local configuration (HONEYGAIN_TOKEN) from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import threading
import time

# Set CustomTkinter appearance mode and theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Define color palette - Cyberpunk/Neon inspired
COLORS = {
    "bg_dark": "#050023",          # Deep blue-black background
    "bg_medium": "#0B0C24",        # Dark blue-black
    "bg_light": "#151A3A",         # Navy blue
    "neon_purple": "#8A2BE2",      # Bright purple
    "neon_blue": "#00BFFF",        # Bright blue
    "neon_pink": "#FF00FF",        # Bright pink
    "neon_cyan": "#00FFFF",        # Bright cyan
    "neon_green": "#39FF14",       # Bright green
    "neon_yellow": "#FFFF33",      # Bright yellow
    "text_primary": "#FFFFFF",     # White text
    "text_secondary": "#AAAAAA",   # Light gray text
    "border_color": "#2A2A4A",     # Border color (no transparency)
}

# Currency exchange rate (1 USD to INR)
USD_TO_INR_RATE = 83.12
# Credit to USD conversion rate (1000 credits = 1 USD)
CREDITS_TO_USD_RATE = 1000

# Function to create a gradient image
def create_gradient(width, height, color1, color2, direction='horizontal'):
    base = Image.new('RGBA', (width, height), color1)
    top = Image.new('RGBA', (width, height), color2)
    mask = Image.new('L', (width, height))
    mask_data = []
    
    if direction == 'horizontal':
        for y in range(height):
            for x in range(width):
                mask_data.append(int(255 * (x / width)))
    else:  # vertical
        for y in range(height):
            for x in range(width):
                mask_data.append(int(255 * (y / height)))
    
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

# Add animated countdown to next refresh
class CircularProgressbar(tk.Canvas):
    def __init__(self, parent, width=60, height=60, progress=0, fg_color=COLORS["neon_blue"], 
                 bg_color=COLORS["bg_dark"], text_color=COLORS["text_primary"], **kwargs):
        super().__init__(parent, width=width, height=height, bg=bg_color, 
                         highlightthickness=0, **kwargs)
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.text_color = text_color
        self.progress = progress
        self.width = width
        self.height = height
        self.draw_progress()
        
    def draw_progress(self):
        self.delete("progress")
        
        # Calculate coordinates
        padding = 10
        x0 = padding
        y0 = padding
        x1 = self.width - padding
        y1 = self.height - padding
        
        # Draw background circle
        self.create_oval(x0, y0, x1, y1, fill=self.bg_color, outline="", tags="progress")
        
        # Convert progress to angle (0-100 to 0-360)
        angle = int(360 * (self.progress / 100))
        
        # Draw progress arc
        self.create_arc(x0, y0, x1, y1, start=90, extent=-angle, 
                       fill=self.fg_color, outline="", tags="progress", style="pieslice")
        
        # Draw center circle (to create a ring effect)
        inner_padding = padding + 8
        self.create_oval(inner_padding, inner_padding, 
                        self.width - inner_padding, self.height - inner_padding, 
                        fill=self.bg_color, outline="", tags="progress")
        
        # Add text in center
        seconds_left = int(self.progress * 0.3)  # Assuming 100% = 30 seconds
        self.create_text(self.width//2, self.height//2, text=f"{seconds_left}s", 
                        fill=self.text_color, font=("Segoe UI", 10), tags="progress")
    
    def set_progress(self, progress):
        self.progress = progress
        self.draw_progress()

# Main application class
class HoneygainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("Honeygain Dashboard")
        self.geometry("1100x750")
        self.minsize(900, 600)
        
        # Set window icon if available
        try:
            self.iconbitmap("icon.ico")
        except:
            pass
        
        # Authorization token
        self.auth_token = os.getenv("HONEYGAIN_TOKEN", "")
        
        # Headers for API requests
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "authorization": f"Bearer {self.auth_token}",
            "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\""
        }
        
        # Data storage
        self.balance_data = None
        self.today_data = None
        self.stats_data = None
        
        # For animations and effects
        self.loading = False
        self.animation_id = None
        
        # Auto-refresh settings
        self.auto_refresh_enabled = True
        self.auto_refresh_interval = 25  # seconds
        self.refresh_timer_id = None
        self.refresh_countdown = 0
        
        # Average earnings data
        self.daily_avg_earnings = 0
        self.estimated_days_to_payout = 0
        
        # Create UI elements
        self.create_ui()
        
        # Start data fetch in a separate thread
        self.fetch_data()
        
        # Start animation loop
        self.animate_elements()
        
        # Start auto-refresh timer
        self.start_auto_refresh_timer()
    
    def start_auto_refresh_timer(self):
        """Start auto-refresh timer"""
        if self.refresh_timer_id:
            self.after_cancel(self.refresh_timer_id)
            
        self.refresh_countdown = 0
        self.update_refresh_progress()
    
    def update_refresh_progress(self):
        """Update refresh progress and fetch data when timer completes"""
        # Update countdown
        self.refresh_countdown += 1
        progress = (self.refresh_countdown / self.auto_refresh_interval) * 100
        
        # Update progress indicator if available
        if hasattr(self, 'refresh_progress'):
            self.refresh_progress.set_progress(progress)
        
        # Check if it's time to refresh
        if self.refresh_countdown >= self.auto_refresh_interval and self.auto_refresh_enabled:
            self.fetch_data()
            self.refresh_countdown = 0
        
        # Schedule next update
        self.refresh_timer_id = self.after(1000, self.update_refresh_progress)
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh on/off"""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        
        # Update button appearance based on state
        if self.auto_refresh_enabled:
            self.auto_refresh_btn.configure(
                text="AUTO-REFRESH: ON",
                fg_color=COLORS["neon_green"],
                hover_color="#2ca616"  # Darker green
            )
        else:
            self.auto_refresh_btn.configure(
                text="AUTO-REFRESH: OFF", 
                fg_color=COLORS["neon_pink"],
                hover_color="#d42fb2"  # Darker pink
            )

    def animate_elements(self):
        """Animate UI elements"""
        # Cancel any existing animation
        if self.animation_id:
            self.after_cancel(self.animation_id)
        
        # Animate loading spinner if loading
        if hasattr(self, 'loading_angle') and self.loading:
            self.loading_angle = (self.loading_angle + 10) % 360
            if hasattr(self, 'loading_canvas'):
                self.draw_loading_spinner(self.loading_canvas, self.loading_angle)
        
        # Pulse effect on cards
        if hasattr(self, 'balance_card'):
            # Add subtle glow effect that pulses
            pass
        
        # Schedule next animation frame
        self.animation_id = self.after(50, self.animate_elements)
    
    def draw_loading_spinner(self, canvas, angle):
        """Draw a loading spinner on the given canvas"""
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        canvas.delete("spinner")
        
        if width <= 1 or height <= 1:  # Not yet properly sized
            return
            
        center_x = width // 2
        center_y = height // 2
        radius = min(width, height) // 2 - 5
        
        # Draw arcs with gradient color
        for i in range(8):
            arc_angle = (angle + i * 45) % 360
            arc_width = 3
            arc_color = COLORS["neon_cyan"] if i == 0 else COLORS["neon_blue"] if i < 4 else COLORS["neon_purple"]
            opacity = max(0.3, 1 - (i * 0.1))
            
            canvas.create_arc(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                start=arc_angle, extent=30, width=arc_width,
                outline=arc_color, style="arc", tags="spinner"
            )
    
    def create_ui(self):
        """Create the main UI elements"""
        # Main container - a grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Content
        self.grid_rowconfigure(2, weight=0)  # Footer
        
        # Create header
        self.create_header()
        
        # Create tabview for main content
        self.tabview = ctk.CTkTabview(self, corner_radius=0)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Add tabs
        self.tab_dashboard = self.tabview.add("DASHBOARD")
        self.tab_stats = self.tabview.add("STATS")
        self.tab_graphs = self.tabview.add("GRAPHS")
        
        # Configure tab styling
        for tab in [self.tab_dashboard, self.tab_stats, self.tab_graphs]:
            tab.configure(fg_color=COLORS["bg_medium"])
        
        # Configure the internal layout of each tab
        for tab in [self.tab_dashboard, self.tab_stats, self.tab_graphs]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
        
        # Create content for each tab
        self.create_dashboard_tab()
        self.create_stats_tab()
        self.create_graphs_tab()
        
        # Create footer
        self.create_footer()
    
    def create_header(self):
        """Create the application header"""
        # Header frame
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["bg_dark"])
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0)
        self.header_frame.grid_columnconfigure(2, weight=0)
        
        # App title with neon effect
        title_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w", padx=20, pady=10)
        
        # Main title
        app_title = ctk.CTkLabel(
            title_frame, 
            text="HONEYGAIN DASHBOARD", 
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=COLORS["neon_cyan"]
        )
        app_title.pack(pady=5)
        
        # Subtitle
        app_subtitle = ctk.CTkLabel(
            title_frame, 
            text="Real-time Earnings Monitor", 
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_secondary"]
        )
        app_subtitle.pack()
        
        # Auto-refresh controls
        refresh_control = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        refresh_control.grid(row=0, column=1, sticky="e", padx=20, pady=10)
        
        # Circular progress indicator
        self.refresh_progress = CircularProgressbar(
            refresh_control,
            width=40, 
            height=40,
            fg_color=COLORS["neon_green"],
            bg_color=COLORS["bg_dark"],
            text_color=COLORS["text_primary"]
        )
        self.refresh_progress.pack(side="left", padx=5)
        
        # Auto-refresh toggle button
        self.auto_refresh_btn = ctk.CTkButton(
            refresh_control,
            text="AUTO-REFRESH: ON",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=COLORS["neon_green"],
            hover_color="#2ca616",  # Darker green
            corner_radius=5,
            command=self.toggle_auto_refresh,
            width=130
        )
        self.auto_refresh_btn.pack(side="left", padx=10)
        
        # Status indicator 
        self.status_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.status_frame.grid(row=0, column=2, sticky="e", padx=20, pady=10)
        
        # Loading animation placeholder
        self.loading_canvas = tk.Canvas(
            self.status_frame, 
            width=30, 
            height=30, 
            bg=COLORS["bg_dark"], 
            highlightthickness=0
        )
        self.loading_canvas.pack(side="left", padx=10)
        self.loading_angle = 0
        
        # Status text
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(side="left", padx=5)
    
    def create_footer(self):
        """Create the application footer"""
        # Footer frame
        self.footer_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["bg_dark"], height=50)
        self.footer_frame.grid(row=2, column=0, sticky="ew")
        self.footer_frame.grid_columnconfigure(0, weight=1)
        self.footer_frame.grid_columnconfigure(1, weight=0)
        
        # Last updated info on left
        self.update_time_var = tk.StringVar()
        self.update_time_var.set("Last update: Never")
        update_label = ctk.CTkLabel(
            self.footer_frame,
            textvariable=self.update_time_var,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLORS["text_secondary"]
        )
        update_label.grid(row=0, column=0, sticky="w", padx=20, pady=10)
        
        # Refresh button on right
        self.refresh_button = ctk.CTkButton(
            self.footer_frame,
            text="REFRESH",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=COLORS["neon_purple"],
            hover_color=COLORS["neon_pink"],
            corner_radius=5,
            command=self.fetch_data
        )
        self.refresh_button.grid(row=0, column=1, sticky="e", padx=20, pady=10)
    
    def create_glass_card(self, parent, title, height=None):
        """Create a card with glass effect"""
        # Main frame with glass-like appearance
        card = ctk.CTkFrame(
            parent,
            corner_radius=15,
            fg_color=COLORS["bg_light"],
            border_width=1,
            border_color=COLORS["border_color"]  # Using solid color instead of transparency
        )
        
        # Add card header with gradient
        header = ctk.CTkFrame(card, corner_radius=10, fg_color="transparent", height=40)
        header.pack(fill="x", padx=5, pady=(5, 0))
        
        # Add title with cool styling
        title_label = ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLORS["neon_cyan"]
        )
        title_label.pack(side="left", padx=15, pady=10)
        
        # Add a divider line with gradient effect
        divider = ctk.CTkFrame(
            card,
            height=2,
            fg_color=COLORS["neon_blue"],
            corner_radius=1
        )
        divider.pack(fill="x", padx=10, pady=(0, 10))
        
        # Content frame
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=10)
        
        if height:
            card.configure(height=height)
            
        return card, content
    
    def create_dashboard_tab(self):
        """Create the dashboard tab content"""
        # Create scrollable container
        dashboard_container = ctk.CTkScrollableFrame(
            self.tab_dashboard,
            fg_color="transparent"
        )
        dashboard_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        dashboard_container.grid_columnconfigure(0, weight=1)
        
        # Balance Card with Progress Bar
        self.balance_card, balance_content = self.create_glass_card(
            dashboard_container, "ACCOUNT BALANCE"
        )
        self.balance_card.pack(fill="x", pady=(0, 15), padx=5)
        
        # Progress bar for payout
        progress_container = ctk.CTkFrame(balance_content, fg_color="transparent")
        progress_container.pack(fill="x", padx=10, pady=10)
        progress_container.grid_columnconfigure(0, weight=1)
        progress_container.grid_columnconfigure(1, weight=0)
        
        # Progress title and info
        progress_title = ctk.CTkLabel(
            progress_container, 
            text="PROGRESS TO PAYOUT",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        progress_title.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        # Add estimated time to payout
        self.payout_time_label = ctk.CTkLabel(
            progress_container,
            text="Estimated: Calculating...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["neon_yellow"]
        )
        self.payout_time_label.grid(row=0, column=1, sticky="e", padx=5, pady=5)
        
        # Glowing progress bar with animation
        self.payout_progress = ctk.CTkProgressBar(
            progress_container,
            width=400,
            height=15,
            corner_radius=7,
            progress_color=COLORS["neon_green"],
            fg_color=COLORS["bg_dark"]
        )
        self.payout_progress.grid(row=1, column=0, sticky="ew", padx=5, pady=5, columnspan=2)
        self.payout_progress.set(0)  # Initial value
        
        # Progress text
        self.payout_text = ctk.CTkLabel(
            progress_container,
            text="0 / 20000 credits",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_secondary"]
        )
        self.payout_text.grid(row=2, column=0, sticky="e", padx=5, pady=5, columnspan=2)
        
        # Balance info grid
        balance_grid = ctk.CTkFrame(balance_content, fg_color="transparent")
        balance_grid.pack(fill="x", padx=10, pady=10)
        
        # Configure grid columns
        balance_grid.grid_columnconfigure(0, weight=1)
        balance_grid.grid_columnconfigure(1, weight=1)
        balance_grid.grid_columnconfigure(2, weight=1)
        
        # Create balance info boxes
        self.balance_info = {
            "current": self.create_info_box(
                balance_grid, "CURRENT BALANCE", "Loading...", COLORS["neon_cyan"], 0, 0
            ),
            "payout": self.create_info_box(
                balance_grid, "PAYOUT BALANCE", "Loading...", COLORS["neon_green"], 0, 1
            ),
            "minimum": self.create_info_box(
                balance_grid, "MINIMUM PAYOUT", "Loading...", COLORS["neon_yellow"], 0, 2
            )
        }
        
        # Add Earnings Average Card
        self.averages_card, averages_content = self.create_glass_card(
            dashboard_container, "EARNINGS AVERAGES"
        )
        self.averages_card.pack(fill="x", pady=(0, 15), padx=5)
        
        # Averages grid
        averages_grid = ctk.CTkFrame(averages_content, fg_color="transparent")
        averages_grid.pack(fill="x", padx=10, pady=10)
        
        # Configure grid columns
        averages_grid.grid_columnconfigure(0, weight=1)
        averages_grid.grid_columnconfigure(1, weight=1)
        averages_grid.grid_columnconfigure(2, weight=1)
        
        # Create averages info boxes
        self.averages_info = {
            "daily": self.create_info_box(
                averages_grid, "DAILY AVERAGE", "Loading...", COLORS["neon_blue"], 0, 0
            ),
            "weekly": self.create_info_box(
                averages_grid, "WEEKLY AVERAGE", "Loading...", COLORS["neon_purple"], 0, 1
            ),
            "monthly": self.create_info_box(
                averages_grid, "MONTHLY AVERAGE", "Loading...", COLORS["neon_pink"], 0, 2
            )
        }
        
        # Today's Earnings Card
        self.today_card, today_content = self.create_glass_card(
            dashboard_container, "TODAY'S EARNINGS"
        )
        self.today_card.pack(fill="x", pady=(0, 15), padx=5)
        
        # Today's total with large display
        self.today_total_frame = ctk.CTkFrame(
            today_content, 
            fg_color=COLORS["bg_medium"],
            corner_radius=10
        )
        self.today_total_frame.pack(fill="x", padx=10, pady=10)
        
        self.today_total_label = ctk.CTkLabel(
            self.today_total_frame,
            text="TODAY: Loading...",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=COLORS["neon_green"]
        )
        self.today_total_label.pack(pady=15)
        
        # Earnings breakdown grid
        earnings_grid = ctk.CTkFrame(today_content, fg_color="transparent")
        earnings_grid.pack(fill="x", padx=10, pady=10)
        
        # Configure grid columns
        earnings_grid.grid_columnconfigure(0, weight=1)
        earnings_grid.grid_columnconfigure(1, weight=1)
        
        # Create earnings info boxes - First row
        self.today_info = {
            "sharing": self.create_info_box(
                earnings_grid, "SHARING", "Loading...", COLORS["neon_cyan"], 0, 0
            ),
            "content": self.create_info_box(
                earnings_grid, "CONTENT", "Loading...", COLORS["neon_blue"], 0, 1
            ),
            "winning": self.create_info_box(
                earnings_grid, "WINNING", "Loading...", COLORS["neon_pink"], 1, 0
            ),
            "referrals": self.create_info_box(
                earnings_grid, "REFERRALS", "Loading...", COLORS["neon_purple"], 1, 1
            )
        }
        
        # Traffic and streaming info
        traffic_frame = ctk.CTkFrame(
            today_content,
            fg_color=COLORS["bg_medium"],
            corner_radius=10
        )
        traffic_frame.pack(fill="x", padx=10, pady=10)
        
        # Configure grid
        traffic_frame.grid_columnconfigure(0, weight=1)
        traffic_frame.grid_columnconfigure(1, weight=1)
        
        # Traffic label with icon
        self.traffic_label = ctk.CTkLabel(
            traffic_frame,
            text="TRAFFIC: Loading...",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=COLORS["text_primary"]
        )
        self.traffic_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Streaming label with icon
        self.streaming_label = ctk.CTkLabel(
            traffic_frame,
            text="STREAMING: Loading...",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=COLORS["text_primary"]
        )
        self.streaming_label.grid(row=0, column=1, padx=20, pady=15, sticky="w")
    
    def create_info_box(self, parent, title, value, accent_color, row, col):
        """Create an info box with title and value"""
        # Frame with slight transparency and border
        frame = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_medium"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border_color"]  # Using solid color instead of transparency
        )
        frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        
        # Title with accent color
        title_label = ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=accent_color
        )
        title_label.pack(anchor="w", padx=15, pady=(10, 5))
        
        # Value with larger font
        value_label = ctk.CTkLabel(
            frame,
            text=value,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        value_label.pack(anchor="w", padx=15, pady=(0, 10))
        
        return value_label

    def create_stats_tab(self):
        """Create the stats tab content"""
        # Create scrollable container
        stats_container = ctk.CTkScrollableFrame(
            self.tab_stats,
            fg_color="transparent"
        )
        stats_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        stats_container.grid_columnconfigure(0, weight=1)
        
        # Monthly Summary Card
        monthly_card, monthly_content = self.create_glass_card(
            stats_container, "MONTHLY SUMMARY"
        )
        monthly_card.pack(fill="x", pady=(0, 15), padx=5)
        
        # Monthly info grid
        monthly_grid = ctk.CTkFrame(monthly_content, fg_color="transparent")
        monthly_grid.pack(fill="x", padx=10, pady=10)
        
        # Configure grid columns
        monthly_grid.grid_columnconfigure(0, weight=1)
        monthly_grid.grid_columnconfigure(1, weight=1)
        monthly_grid.grid_columnconfigure(2, weight=1)
        
        # Create monthly info boxes
        self.monthly_info = {
            "current": self.create_info_box(
                monthly_grid, "CURRENT MONTH", "Loading...", COLORS["neon_green"], 0, 0
            ),
            "average": self.create_info_box(
                monthly_grid, "DAILY AVERAGE", "Loading...", COLORS["neon_blue"], 0, 1
            ),
            "last": self.create_info_box(
                monthly_grid, "LAST MONTH", "Loading...", COLORS["neon_purple"], 0, 2
            )
        }
        
        # Recent Earnings Table Card
        earnings_card, earnings_content = self.create_glass_card(
            stats_container, "RECENT EARNINGS"
        )
        earnings_card.pack(fill="x", expand=True, pady=(0, 15), padx=5)
        
        # Create table container
        table_container = ctk.CTkFrame(earnings_content, fg_color="transparent")
        table_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Table headers
        headers = ["DATE", "TOTAL", "SHARING", "CONTENT", "WINNING", "REFERRALS"]
        header_colors = [
            COLORS["text_primary"], 
            COLORS["neon_green"], 
            COLORS["neon_cyan"], 
            COLORS["neon_blue"], 
            COLORS["neon_pink"], 
            COLORS["neon_purple"]
        ]
        
        # Headers frame
        header_frame = ctk.CTkFrame(table_container, fg_color=COLORS["bg_medium"])
        header_frame.pack(fill="x", padx=2, pady=2)
        
        # Configure columns for headers
        for i in range(len(headers)):
            header_frame.grid_columnconfigure(i, weight=1)
        
        # Create header labels
        for i, header in enumerate(headers):
            header_label = ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=header_colors[i]
            )
            header_label.grid(row=0, column=i, padx=5, pady=10, sticky="w")
        
        # Table content scrollable frame
        self.table_frame = ctk.CTkScrollableFrame(
            table_container,
            fg_color="transparent",
            height=300
        )
        self.table_frame.pack(fill="both", expand=True, padx=2, pady=(5, 0))
        
        # Configure columns for data
        for i in range(len(headers)):
            self.table_frame.grid_columnconfigure(i, weight=1)
        
        # Table will be populated with data later
    
    def create_graphs_tab(self):
        """Create the graphs tab content"""
        # Create scrollable container
        graphs_container = ctk.CTkScrollableFrame(
            self.tab_graphs,
            fg_color="transparent"
        )
        graphs_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        graphs_container.grid_columnconfigure(0, weight=1)
        
        # Main Earnings Chart Card
        chart_card, chart_content = self.create_glass_card(
            graphs_container, "DAILY EARNINGS (LAST 14 DAYS)"
        )
        chart_card.pack(fill="x", expand=True, pady=(0, 15), padx=5)
        
        # Placeholder for the matplotlib chart
        self.chart_frame = ctk.CTkFrame(chart_content, fg_color="transparent", height=350)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Stats summary below the chart
        stats_frame = ctk.CTkFrame(chart_content, fg_color="transparent")
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        # Configure grid columns
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_columnconfigure(1, weight=1)
        stats_frame.grid_columnconfigure(2, weight=1)
        
        # Stats info boxes
        self.chart_stats = {
            "total": self.create_info_box(
                stats_frame, "TOTAL EARNINGS", "Loading...", COLORS["neon_green"], 0, 0
            ),
            "average": self.create_info_box(
                stats_frame, "AVERAGE DAILY", "Loading...", COLORS["neon_blue"], 0, 1
            ),
            "best": self.create_info_box(
                stats_frame, "BEST DAY", "Loading...", COLORS["neon_pink"], 0, 2
            )
        }
        
        # Earnings Breakdown Pie Chart
        pie_card, pie_content = self.create_glass_card(
            graphs_container, "EARNINGS BREAKDOWN"
        )
        pie_card.pack(fill="x", pady=(0, 15), padx=5)
        
        # Create a frame to hold two charts side by side
        charts_grid = ctk.CTkFrame(pie_content, fg_color="transparent")
        charts_grid.pack(fill="x", padx=10, pady=10)
        charts_grid.grid_columnconfigure(0, weight=1)
        charts_grid.grid_columnconfigure(1, weight=1)
        
        # Placeholder for pie chart
        self.pie_frame = ctk.CTkFrame(
            charts_grid, 
            fg_color=COLORS["bg_medium"],
            corner_radius=10,
            height=250
        )
        self.pie_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Placeholder for bar chart
        self.bar_frame = ctk.CTkFrame(
            charts_grid, 
            fg_color=COLORS["bg_medium"],
            corner_radius=10,
            height=250
        )
        self.bar_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
    
    def update_table(self):
        """Update the earnings table with data"""
        # Clear existing table rows
        for widget in self.table_frame.winfo_children():
            widget.destroy()
            
        if not self.stats_data:
            return
            
        # Sort the dates
        sorted_dates = sorted(self.stats_data.keys())
        
        # Get the last 30 days (or less if not enough data)
        recent_dates = sorted_dates[-30:]
        
        # Row colors for alternating rows
        row_colors = [COLORS["bg_medium"], COLORS["bg_light"]]
        
        # Add data rows
        for i, date in enumerate(recent_dates):
            row_color = row_colors[i % 2]
            day_data = self.stats_data[date]
            
            # Calculate totals
            gathering = day_data.get("gathering", {}).get("credits", 0)
            content = day_data.get("content_delivery", {}).get("credits", 0)
            winnings = day_data.get("winnings", {}).get("credits", 0)
            referrals = day_data.get("referrals", {}).get("credits", 0)
            
            total = gathering + content + winnings + referrals
            
            # Skip days with zero earnings
            if total <= 0.01:
                continue
                
            # Create row frame
            row_frame = ctk.CTkFrame(self.table_frame, fg_color=row_color)
            row_frame.pack(fill="x", padx=2, pady=1)
            
            # Configure columns
            for i in range(6):
                row_frame.grid_columnconfigure(i, weight=1)
            
            # Cell data with colors based on values
            cells = [
                {"text": date, "color": COLORS["text_primary"]},
                {"text": f"{total:.2f}", "color": COLORS["neon_green"] if total > 0 else COLORS["text_secondary"]},
                {"text": f"{gathering:.2f}", "color": COLORS["neon_cyan"] if gathering > 0 else COLORS["text_secondary"]},
                {"text": f"{content:.2f}", "color": COLORS["neon_blue"] if content > 0 else COLORS["text_secondary"]},
                {"text": f"{winnings:.2f}", "color": COLORS["neon_pink"] if winnings > 0 else COLORS["text_secondary"]},
                {"text": f"{referrals:.2f}", "color": COLORS["neon_purple"] if referrals > 0 else COLORS["text_secondary"]}
            ]
            
            # Create cells
            for j, cell in enumerate(cells):
                cell_label = ctk.CTkLabel(
                    row_frame,
                    text=cell["text"],
                    font=ctk.CTkFont(family="Segoe UI", size=12),
                    text_color=cell["color"]
                )
                cell_label.grid(row=0, column=j, padx=5, pady=10, sticky="w")
    
    def calculate_time_to_payout(self):
        """Calculate estimated time to reach minimum payout based on last 7 days average"""
        if not self.balance_data or not self.daily_avg_earnings or self.daily_avg_earnings <= 0:
            return "Unknown"
            
        # Get payout info
        payout_credits = self.balance_data["payout"]["credits"]
        min_payout_credits = self.balance_data["min_payout"]["credits"]
        
        # Calculate remaining credits needed
        remaining_credits = min_payout_credits - payout_credits
        
        # Calculate days based on average daily earnings (from last 7 days)
        if remaining_credits <= 0:
            self.estimated_days_to_payout = 0
            return "Ready for payout!"
            
        self.estimated_days_to_payout = remaining_credits / self.daily_avg_earnings
        
        # Format the result
        if self.estimated_days_to_payout < 1:
            hours = int(self.estimated_days_to_payout * 24)
            return f"About {hours} hours"
        elif self.estimated_days_to_payout < 30:
            days = int(self.estimated_days_to_payout)
            return f"About {days} days"
        else:
            months = self.estimated_days_to_payout / 30
            return f"About {months:.1f} months"
    
    def animate_value_change(self, label, target_value, prefix="", suffix="", duration=1000, fps=30, decimal_places=2):
        """Animate a value changing with counting effect"""
        # Get current value
        current_text = label.cget("text")
        
        # Try to extract current number
        try:
            # Extract the first number found in the text
            import re
            match = re.search(r"([0-9]*\.?[0-9]+)", current_text)
            if match:
                current_value = float(match.group(1))
            else:
                current_value = 0
        except:
            current_value = 0
        
        # Calculate parameters
        steps = int(fps * duration / 1000)
        if steps <= 0:
            steps = 1
        
        step_size = (target_value - current_value) / steps
        
        # Define update function
        def update_value(step):
            if step > steps:
                # Final update with exact target
                label.configure(text=f"{prefix}{target_value:.{decimal_places}f}{suffix}")
                return
                
            new_value = current_value + step_size * step
            label.configure(text=f"{prefix}{new_value:.{decimal_places}f}{suffix}")
            
            # Schedule next update
            label.after(int(duration / steps), lambda: update_value(step + 1))
        
        # Start animation
        update_value(1)
    
    def fetch_balance(self):
        """Fetch user balance data"""
        endpoint = "https://dashboard.honeygain.com/api/v1/users/balances"
        response = requests.get(endpoint, headers=self.headers)
        
        if response.status_code == 200:
            self.balance_data = response.json()["data"]
            
            # Get balance values
            realtime_credits = self.balance_data["realtime"]["credits"]
            payout_credits = self.balance_data["payout"]["credits"]
            min_payout_credits = self.balance_data["min_payout"]["credits"]
            
            # Calculate progress percentage
            progress_percentage = (payout_credits / min_payout_credits) if min_payout_credits > 0 else 0
            
            # Update UI in the main thread
            self.after(0, lambda: self.payout_progress.set(progress_percentage))
            self.after(0, lambda: self.payout_text.configure(
                text=f"{payout_credits:.2f} / {min_payout_credits:.2f} credits"
            ))
            
            # Update balance info with USD and INR
            self.after(0, lambda: self.balance_info["current"].configure(
                text=f"{realtime_credits:.2f} credits\n(${realtime_credits/CREDITS_TO_USD_RATE:.2f} | â‚¹{(realtime_credits/CREDITS_TO_USD_RATE)*USD_TO_INR_RATE:.2f})"
            ))
            self.after(0, lambda: self.balance_info["payout"].configure(
                text=f"{payout_credits:.2f} credits\n(${payout_credits/CREDITS_TO_USD_RATE:.2f} | â‚¹{(payout_credits/CREDITS_TO_USD_RATE)*USD_TO_INR_RATE:.2f})"
            ))
            self.after(0, lambda: self.balance_info["minimum"].configure(
                text=f"{min_payout_credits:.2f} credits\n(${min_payout_credits/CREDITS_TO_USD_RATE:.2f} | â‚¹{(min_payout_credits/CREDITS_TO_USD_RATE)*USD_TO_INR_RATE:.2f})"
            ))
            
            # Calculate time to payout after stats are fetched (needs average daily earnings)
            if hasattr(self, 'daily_avg_earnings') and self.daily_avg_earnings > 0:
                payout_estimation = self.calculate_time_to_payout()
                self.after(0, lambda: self.payout_time_label.configure(
                    text=f"Estimated: {payout_estimation}"
                ))
        else:
            print(f"Failed to fetch balance: {response.status_code} - {response.text}")
    
    def fetch_stats(self):
        """Fetch stats data"""
        endpoint = "https://dashboard.honeygain.com/api/v1/earnings/stats"
        response = requests.get(endpoint, headers=self.headers)
        
        if response.status_code == 200:
            self.stats_data = response.json()
            
            # Get current date for comparison
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Sort dates and filter out current day
            sorted_dates = sorted([d for d in self.stats_data.keys() if d != current_date])
            
            # Get the last 7 complete days of data (or less if not enough data)
            recent_dates = sorted_dates[-7:] if len(sorted_dates) >= 7 else sorted_dates
            
            # Extract daily values from complete days only
            daily_values = []
            
            for date in recent_dates:
                day_data = self.stats_data[date]
                
                # Calculate total for the day
                day_total = (
                    day_data.get("gathering", {}).get("credits", 0) +
                    day_data.get("content_delivery", {}).get("credits", 0) +
                    day_data.get("winnings", {}).get("credits", 0) +
                    day_data.get("referrals", {}).get("credits", 0)
                )
                
                if day_total > 0:
                    daily_values.append(day_total)
            
            # If no valid data found, use fallback values
            if not daily_values:
                daily_values = [0]
            
            # Calculate averages based on the last 7 complete days
            self.daily_avg_earnings = sum(daily_values) / len(daily_values)
            weekly_avg = sum(daily_values)  # Total earnings for the week
            
            # If we have less than 7 days of data, extrapolate to 7 days
            if len(daily_values) < 7 and len(daily_values) > 0:
                weekly_avg = self.daily_avg_earnings * 7
            
            monthly_avg = self.daily_avg_earnings * 30  # Extrapolate to a month (30 days)
            
            # Calculate monthly and full month stats for display
            current_month_total = 0
            last_month_total = 0
            
            current_month = datetime.now().strftime("%Y-%m")
            
            # Count days with data in current month (excluding today)
            current_month_days = sum(1 for d in sorted_dates if d.startswith(current_month))
            
            for date, day_data in self.stats_data.items():
                # Skip current day for stats
                if date == current_date:
                    continue
                
                # Calculate total for the day
                day_total = (
                    day_data.get("gathering", {}).get("credits", 0) +
                    day_data.get("content_delivery", {}).get("credits", 0) +
                    day_data.get("winnings", {}).get("credits", 0) +
                    day_data.get("referrals", {}).get("credits", 0)
                )
                
                # Check if this is current month
                if date.startswith(current_month):
                    current_month_total += day_total
                
                # Check if this is last month
                last_month = datetime.now().replace(day=1)
                last_month = last_month.replace(month=last_month.month-1 if last_month.month > 1 else 12)
                last_month_str = last_month.strftime("%Y-%m")
                
                if date.startswith(last_month_str):
                    last_month_total += day_total
            
            # Update monthly stats in the main thread with USD and INR
            self.after(0, lambda: self.monthly_info["current"].configure(
                text=f"{current_month_total:.2f}\n(${current_month_total/CREDITS_TO_USD_RATE:.2f} | â‚¹{(current_month_total/CREDITS_TO_USD_RATE)*USD_TO_INR_RATE:.2f})"
            ))
            self.after(0, lambda: self.monthly_info["average"].configure(
                text=f"{self.daily_avg_earnings:.2f}\n(${self.daily_avg_earnings/CREDITS_TO_USD_RATE:.2f} | â‚¹{(self.daily_avg_earnings/CREDITS_TO_USD_RATE)*USD_TO_INR_RATE:.2f})"
            ))
            self.after(0, lambda: self.monthly_info["last"].configure(
                text=f"{last_month_total:.2f}\n(${last_month_total/CREDITS_TO_USD_RATE:.2f} | â‚¹{(last_month_total/CREDITS_TO_USD_RATE)*USD_TO_INR_RATE:.2f})"
            ))
            
            # Update UI elements with calculation source info
            days_used_text = f"Based on last {len(daily_values)} complete days"
            
            # Update earnings averages with animations
            self.after(0, lambda: self.animate_value_change(
                self.averages_info["daily"], 
                self.daily_avg_earnings, 
                suffix=f" credits\n(${self.daily_avg_earnings/CREDITS_TO_USD_RATE:.2f} | â‚¹{(self.daily_avg_earnings/CREDITS_TO_USD_RATE)*USD_TO_INR_RATE:.2f})"
            ))
            
            self.after(500, lambda: self.animate_value_change(  # Delay starting each animation
                self.averages_info["weekly"], 
                weekly_avg, 
                suffix=f" credits\n(${weekly_avg/CREDITS_TO_USD_RATE:.2f} | â‚¹{(weekly_avg/CREDITS_TO_USD_RATE)*USD_TO_INR_RATE:.2f})"
            ))
            
            self.after(1000, lambda: self.animate_value_change(  # Delay starting each animation
                self.averages_info["monthly"], 
                monthly_avg, 
                suffix=f" credits\n(${monthly_avg/CREDITS_TO_USD_RATE:.2f} | â‚¹{(monthly_avg/CREDITS_TO_USD_RATE)*USD_TO_INR_RATE:.2f})"
            ))
            
            # Calculate and update time to payout
            payout_estimation = self.calculate_time_to_payout()
            self.after(0, lambda: self.payout_time_label.configure(
                text=f"Estimated: {payout_estimation} ({days_used_text})"
            ))
        else:
            print(f"Failed to fetch stats: {response.status_code} - {response.text}")

    def fetch_data(self):
        """Fetch data from Honeygain API"""
        # Set loading state
        self.loading = True
        self.status_var.set("Fetching data...")
        self.refresh_button.configure(state="disabled")
        
        # Start a new thread for data fetching
        threading.Thread(target=self._fetch_data_thread, daemon=True).start()

    def _fetch_data_thread(self):
        """Thread function to fetch data"""
        try:
            # Fetch all data
            self.fetch_balance()
            self.fetch_today()
            self.fetch_stats()
            
            # Update UI in the main thread
            self.after(0, self._update_ui_after_fetch)
            
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            # Update status in main thread
            self.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
            self.after(0, lambda: self.refresh_button.configure(state="normal"))
            self.after(0, lambda: setattr(self, 'loading', False))

    def _update_ui_after_fetch(self):
        """Update UI after data fetch completes"""
        # Update all UI components
        self.update_table()
        self.update_graphs()
        
        # Update timestamp
        current_time = datetime.now().strftime("%H:%M:%S")
        self.update_time_var.set(f"Last updated: {current_time}")
        
        # Reset loading state
        self.loading = False
        self.status_var.set("Ready")
        self.refresh_button.configure(state="normal")
        
        # Add cool glow animation to indicate fresh data
        self.animate_refresh()

    def animate_refresh(self):
        """Animate a refresh effect on the dashboard cards"""
        # Add a brief glow effect to the cards
        if hasattr(self, 'balance_card'):
            self._pulse_border(self.balance_card)
        
        if hasattr(self, 'today_card'):
            self._pulse_border(self.today_card)

    def _pulse_border(self, widget, count=0, max_count=10):
        """Create pulsing border effect"""
        if count >= max_count:
            # Reset border
            widget.configure(border_color=COLORS["border_color"])
            return
        
        # Calculate color intensity based on sine wave
        intensity = int(127 * math.sin(count * 0.6) + 128)
        color = f"#{intensity:02x}{intensity:02x}ff"  # Blue glow
        
        # Update border
        widget.configure(border_color=color)
        
        # Schedule next pulse
        self.after(50, lambda: self._pulse_border(widget, count + 1, max_count))

    def fetch_today(self):
        """Fetch today's earnings data"""
        endpoint = "https://dashboard.honeygain.com/api/v1/earnings/today"
        response = requests.get(endpoint, headers=self.headers)
        
        if response.status_code == 200:
            self.today_data = response.json()
            
            # Extract values
            total_credits = self.today_data["total_credits"]
            gathering_credits = self.today_data["gathering"]["credits"]
            cdn_credits = self.today_data["cdn"]["credits"]
            winning_credits = self.today_data["winning"]["credits"]
            referral_credits = self.today_data["referral"]["credits"]
            
            # Traffic and streaming data
            gathering_bytes = self.today_data["gathering_bytes"]
            streaming_seconds = self.today_data["streaming_seconds"]
            
            # Format traffic display
            if gathering_bytes > 1_000_000_000:
                traffic_display = f"{gathering_bytes / 1_000_000_000:.2f} GB"
            else:
                traffic_display = f"{gathering_bytes / 1_000_000:.2f} MB"
            
            # Format streaming display
            hours = streaming_seconds // 3600
            minutes = (streaming_seconds % 3600) // 60
            streaming_display = f"{hours}h {minutes}m"
            
            # Update UI in the main thread
            self.after(0, lambda: self.today_total_label.configure(
                text=f"{total_credits:.2f} credits (${total_credits/CREDITS_TO_USD_RATE:.2f} | â‚¹{(total_credits/CREDITS_TO_USD_RATE)*USD_TO_INR_RATE:.2f})"
            ))
            
            self.after(0, lambda: self.today_info["sharing"].configure(
                text=f"{gathering_credits:.2f} credits"
            ))
            self.after(0, lambda: self.today_info["content"].configure(
                text=f"{cdn_credits:.2f} credits"
            ))
            self.after(0, lambda: self.today_info["winning"].configure(
                text=f"{winning_credits:.2f} credits"
            ))
            self.after(0, lambda: self.today_info["referrals"].configure(
                text=f"{referral_credits:.2f} credits"
            ))
            
            self.after(0, lambda: self.traffic_label.configure(
                text=f"TRAFFIC: {traffic_display}"
            ))
            self.after(0, lambda: self.streaming_label.configure(
                text=f"STREAMING: {streaming_display}"
            ))
        else:
            print(f"Failed to fetch today's data: {response.status_code} - {response.text}")

    def update_graphs(self):
        """Update all graphs with data"""
        if not self.stats_data:
            return
        
        # Clear any existing charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        for widget in self.pie_frame.winfo_children():
            widget.destroy()
        
        for widget in self.bar_frame.winfo_children():
            widget.destroy()
        
        # Extract data for the main chart
        dates = []
        gathering_credits = []
        content_credits = []
        winning_credits = []
        
        # Sort the dates
        sorted_dates = sorted(self.stats_data.keys())
        
        # Get the last 14 days (or less if not enough data)
        recent_dates = sorted_dates[-14:]
        
        # Process data
        for date in recent_dates:
            day_data = self.stats_data[date]
            dates.append(date[-5:])  # Format: MM-DD
            
            # Get credits values
            gathering = day_data.get("gathering", {}).get("credits", 0)
            gathering_credits.append(gathering)
            
            content = day_data.get("content_delivery", {}).get("credits", 0)
            content_credits.append(content)
            
            winning = day_data.get("winnings", {}).get("credits", 0)
            winning_credits.append(winning)
        
        # Stats calculations
        total_earnings = sum(gathering_credits) + sum(content_credits) + sum(winning_credits)
        avg_daily = total_earnings / len(recent_dates) if recent_dates else 0
        max_day = max([g+c+w for g, c, w in zip(gathering_credits, content_credits, winning_credits)]) if recent_dates else 0
        
        # Update stats
        self.chart_stats["total"].configure(text=f"{total_earnings:.2f} credits")
        self.chart_stats["average"].configure(text=f"{avg_daily:.2f} credits")
        self.chart_stats["best"].configure(text=f"{max_day:.2f} credits")
        
        # Configure matplotlib style for dark theme
        plt.style.use('dark_background')
        
        # Create the main stacked bar chart
        self.create_stacked_bar_chart(
            self.chart_frame, dates, 
            [gathering_credits, content_credits, winning_credits],
            ["Sharing", "Content", "Winning"],
            [COLORS["neon_cyan"], COLORS["neon_blue"], COLORS["neon_pink"]]
        )
        
        # Create pie chart of earnings breakdown
        self.create_pie_chart(
            self.pie_frame,
            ["Sharing", "Content", "Winning"],
            [sum(gathering_credits), sum(content_credits), sum(winning_credits)],
            [COLORS["neon_cyan"], COLORS["neon_blue"], COLORS["neon_pink"]]
        )
        
        # Create horizontal bar chart
        self.create_horizontal_bar_chart(
            self.bar_frame,
            ["Sharing", "Content", "Winning", "Referrals"],
            [sum(gathering_credits), sum(content_credits), sum(winning_credits), 0],
            [COLORS["neon_cyan"], COLORS["neon_blue"], COLORS["neon_pink"], COLORS["neon_purple"]]
        )

    def create_stacked_bar_chart(self, parent, x_data, y_data_sets, labels, colors):
        """Create a stacked bar chart"""
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 6), facecolor=COLORS["bg_dark"])
        ax.set_facecolor(COLORS["bg_dark"])
        
        # Plot the data
        bottoms = [0] * len(x_data)
        for i, y_data in enumerate(y_data_sets):
            ax.bar(x_data, y_data, bottom=bottoms, label=labels[i], color=colors[i], alpha=0.9)
            # Update bottoms for next layer
            bottoms = [b + y for b, y in zip(bottoms, y_data)]
        
        # Customize plot
        ax.set_xlabel("Date", color=COLORS["text_primary"], fontsize=12)
        ax.set_ylabel("Credits", color=COLORS["text_primary"], fontsize=12)
        ax.tick_params(axis='x', colors=COLORS["text_secondary"], rotation=45)
        ax.tick_params(axis='y', colors=COLORS["text_secondary"])
        
        # Remove spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(COLORS["bg_light"])
        ax.spines['left'].set_color(COLORS["bg_light"])
        
        # Add grid
        ax.grid(axis='y', linestyle='--', alpha=0.2, color=COLORS["text_secondary"])
        
        # Add legend
        legend = ax.legend(facecolor=COLORS["bg_dark"], framealpha=0.9, 
                          edgecolor=COLORS["bg_light"], loc='upper right')
        for text in legend.get_texts():
            text.set_color(COLORS["text_primary"])
        
        plt.tight_layout()
        
        # Embed in frame
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def create_pie_chart(self, parent, labels, values, colors):
        """Create a pie chart"""
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(5, 5), facecolor=COLORS["bg_medium"])
        ax.set_facecolor(COLORS["bg_medium"])
        
        # Check if we have non-zero values
        if sum(values) > 0:
            # Create pie chart
            wedges, texts, autotexts = ax.pie(
                values, 
                labels=None,
                autopct=lambda pct: f"{pct:.1f}%" if pct > 5 else "",
                colors=colors,
                startangle=90,
                wedgeprops={'edgecolor': COLORS["bg_medium"], 'linewidth': 1, 'antialiased': True}
            )
            
            # Style autopct text
            for autotext in autotexts:
                autotext.set_color(COLORS["text_primary"])
                autotext.set_fontsize(9)
        else:
            # No data
            ax.text(0.5, 0.5, "No Data", ha='center', va='center', 
                   fontsize=14, color=COLORS["text_secondary"])
        
        # Add title
        ax.set_title("Earnings Sources", color=COLORS["neon_cyan"], fontsize=14)
        
        # Add legend
        if sum(values) > 0:
            legend = ax.legend(labels, loc="center left", bbox_to_anchor=(1, 0.5),
                              facecolor=COLORS["bg_medium"], framealpha=0.9, 
                              edgecolor=COLORS["bg_light"])
            for text in legend.get_texts():
                text.set_color(COLORS["text_primary"])
        
        plt.tight_layout()
        
        # Embed in frame
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def create_horizontal_bar_chart(self, parent, labels, values, colors):
        """Create a horizontal bar chart"""
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(5, 5), facecolor=COLORS["bg_medium"])
        ax.set_facecolor(COLORS["bg_medium"])
        
        # Create horizontal bar chart
        bars = ax.barh(labels, values, color=colors, alpha=0.9)
        
        # Add values at the end of bars
        for i, bar in enumerate(bars):
            width = bar.get_width()
            if width > 0:
                ax.text(width + max(values) * 0.01, 
                       bar.get_y() + bar.get_height()/2, 
                       f"{width:.2f}", 
                       ha='left', va='center',
                       color=COLORS["text_primary"], fontsize=9)
        
        # Customize plot
        ax.set_xlabel("Credits", color=COLORS["text_primary"], fontsize=11)
        ax.tick_params(axis='x', colors=COLORS["text_secondary"])
        ax.tick_params(axis='y', colors=COLORS["text_primary"])
        
        # Remove spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(COLORS["bg_light"])
        ax.spines['left'].set_color(COLORS["bg_light"])
        
        # Add title
        ax.set_title("Earnings by Source", color=COLORS["neon_blue"], fontsize=14)
        
        plt.tight_layout()
        
        # Embed in frame
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

if __name__ == "__main__":
    root = HoneygainApp()
    root.mainloop()
