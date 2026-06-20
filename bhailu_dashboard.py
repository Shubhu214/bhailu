"""
BHAILU Dashboard — Dark HUD Interface
Tony Stark inspired: world map, system stats, news feed, voice visualizer
"""

import tkinter as tk
from tkinter import font as tkfont
import subprocess, threading, sys, os, json, time, math, random, datetime, html

# ── PALETTE ───────────────────────────────────────────────────────────────────
BG       = "#040810"
PANEL    = "#070e1a"
PANEL2   = "#0a1525"
BORDER   = "#0d2035"
ACCENT   = "#e8420a"       # BHAILU red-orange (vs JARVIS cyan)
ACCENT2  = "#ff6b35"
ACCENT3  = "#ff9966"
BLUE     = "#1a6fff"
CYAN     = "#00cfff"
DIM      = "#3a1408"
TEXT     = "#ffd4b8"
MUTED    = "#5a3020"
SUCCESS  = "#00ff88"
WARN     = "#ffcc00"
DANGER   = "#ff2244"
GRID     = "#0a1a2a"

W, H = 1100, 700

# ── WORLD MAP (SVG-style dots on canvas) ─────────────────────────────────────
# Approximate lat/lon → pixel for a simple equirectangular map
MAP_W, MAP_H = 520, 280

# Major cities with their approx map coords (x%, y%)
HOTSPOTS = [
    ("New York",   0.235, 0.34),
    ("London",     0.465, 0.26),
    ("Paris",      0.475, 0.27),
    ("Moscow",     0.565, 0.22),
    ("Dubai",      0.600, 0.40),
    ("Mumbai",     0.635, 0.43),
    ("Beijing",    0.700, 0.30),
    ("Tokyo",      0.760, 0.31),
    ("Sydney",     0.760, 0.68),
    ("São Paulo",  0.295, 0.63),
    ("Cairo",      0.540, 0.40),
    ("Lagos",      0.490, 0.48),
    ("Singapore",  0.715, 0.50),
    ("LA",         0.130, 0.36),
    ("Chicago",    0.200, 0.32),
    ("Berlin",     0.505, 0.25),
    ("Seoul",      0.745, 0.30),
    ("Bangalore",  0.640, 0.46),
]

# Continent outline approximations as polygon point lists (x%, y%)
CONTINENTS = [
    # North America
    [(0.08,0.18),(0.28,0.18),(0.30,0.25),(0.26,0.30),(0.22,0.38),(0.18,0.45),
     (0.16,0.50),(0.20,0.52),(0.24,0.55),(0.22,0.60),(0.18,0.58),(0.12,0.50),
     (0.08,0.40),(0.06,0.30),(0.08,0.18)],
    # South America
    [(0.22,0.48),(0.30,0.48),(0.34,0.52),(0.35,0.60),(0.33,0.72),(0.28,0.78),
     (0.23,0.75),(0.20,0.65),(0.20,0.55),(0.22,0.48)],
    # Europe
    [(0.44,0.18),(0.56,0.18),(0.58,0.22),(0.56,0.30),(0.50,0.32),(0.46,0.30),
     (0.44,0.25),(0.44,0.18)],
    # Africa
    [(0.46,0.33),(0.56,0.33),(0.60,0.38),(0.60,0.50),(0.56,0.60),(0.52,0.65),
     (0.48,0.62),(0.44,0.55),(0.44,0.42),(0.46,0.33)],
    # Asia
    [(0.56,0.18),(0.80,0.18),(0.84,0.22),(0.82,0.35),(0.76,0.42),(0.68,0.48),
     (0.62,0.48),(0.58,0.42),(0.56,0.32),(0.56,0.18)],
    # Australia
    [(0.72,0.55),(0.82,0.55),(0.84,0.62),(0.80,0.70),(0.72,0.70),(0.70,0.62),
     (0.72,0.55)],
]

class WorldMap(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, width=MAP_W, height=MAP_H,
                         bg=BG, highlightthickness=0, **kw)
        self.t = 0
        self.pulse_spots = [(random.random(), random.random(), random.randint(0,100)) for _ in range(8)]
        self._draw()
        self._animate()

    def _draw(self):
        self.delete("all")
        # Grid lines
        for x in range(0, MAP_W, 40):
            self.create_line(x, 0, x, MAP_H, fill=GRID, width=1)
        for y in range(0, MAP_H, 30):
            self.create_line(0, y, MAP_W, y, fill=GRID, width=1)

        # Continents
        for cont in CONTINENTS:
            pts = [(x * MAP_W, y * MAP_H) for x, y in cont]
            flat = [c for p in pts for c in p]
            self.create_polygon(flat, fill="#0d1f35", outline=BORDER, width=1)

        # Animated scan line
        scan_y = int((math.sin(self.t * 0.03) * 0.5 + 0.5) * MAP_H)
        self.create_line(0, scan_y, MAP_W, scan_y, fill=ACCENT, width=1,
                         stipple="gray25")

        # City hotspots
        for name, xp, yp in HOTSPOTS:
            px, py = xp * MAP_W, yp * MAP_H
            pulse = abs(math.sin(self.t * 0.05 + xp * 10)) * 6 + 2
            self.create_oval(px-pulse, py-pulse, px+pulse, py+pulse,
                             outline=ACCENT2, width=1, fill="")
            self.create_oval(px-2, py-2, px+2, py+2, fill=ACCENT, outline="")

        # Random alert pulses
        for xp, yp, offset in self.pulse_spots:
            px, py = xp * MAP_W, yp * MAP_H
            r = abs(math.sin(self.t * 0.04 + offset)) * 12
            alpha = 1 - r / 12
            if r > 1:
                self.create_oval(px-r, py-r, px+r, py+r,
                                 outline=CYAN, width=1, fill="")

        # Corner brackets
        b = 8
        for cx, cy, dx, dy in [(0,0,1,1),(MAP_W,0,-1,1),(0,MAP_H,1,-1),(MAP_W,MAP_H,-1,-1)]:
            self.create_line(cx, cy, cx+dx*b*2, cy, fill=ACCENT, width=2)
            self.create_line(cx, cy, cx, cy+dy*b*2, fill=ACCENT, width=2)

        # Label
        self.create_text(6, 4, text="GLOBAL SURVEILLANCE", anchor="nw",
                         fill=MUTED, font=("Courier New", 7))
        self.create_text(MAP_W-6, 4, text=f"LIVE", anchor="ne",
                         fill=SUCCESS, font=("Courier New", 7))

    def _animate(self):
        self.t += 1
        self._draw()
        self.after(50, self._animate)


# ── VOICE WAVEFORM ────────────────────────────────────────────────────────────
class VoiceRing(tk.Canvas):
    def __init__(self, parent, size=160, **kw):
        super().__init__(parent, width=size, height=size,
                         bg=BG, highlightthickness=0, **kw)
        self.size = size
        self.cx = size / 2
        self.cy = size / 2
        self.t = 0
        self.state = "idle"
        self._animate()

    def set_state(self, s): self.state = s

    def _draw(self):
        self.delete("all")
        cx, cy = self.cx, self.cy
        t = self.t

        colors = {
            "idle":       (MUTED,    DIM),
            "listening":  (SUCCESS,  "#004422"),
            "thinking":   (WARN,     "#443300"),
            "speaking":   (ACCENT,   DIM),
            "speaking_llm": (ACCENT2, DIM),
        }
        col, col2 = colors.get(self.state, (MUTED, DIM))

        # Background glow
        r_bg = 58 + math.sin(t * 0.06) * 4
        self.create_oval(cx-r_bg, cy-r_bg, cx+r_bg, cy+r_bg,
                         fill=col2, outline="")

        # Waveform bars around ring
        bars = 36
        for i in range(bars):
            angle = (i / bars) * 2 * math.pi - math.pi/2
            if self.state in ("listening", "speaking", "speaking_llm"):
                h = 8 + abs(math.sin(t * 0.12 + i * 0.5)) * 18 + abs(math.sin(t * 0.07 + i * 0.9)) * 8
            elif self.state == "thinking":
                h = 4 + abs(math.sin(t * 0.20 + i * 0.3)) * 10
            else:
                h = 3 + abs(math.sin(i * 0.4 + t * 0.02)) * 4

            r_inner = 45
            r_outer = r_inner + h
            x1 = cx + r_inner * math.cos(angle)
            y1 = cy + r_inner * math.sin(angle)
            x2 = cx + r_outer * math.cos(angle)
            y2 = cy + r_outer * math.sin(angle)
            self.create_line(x1, y1, x2, y2, fill=col, width=2,
                             capstyle=tk.ROUND)

        # Outer ring
        r_out = 44
        self.create_oval(cx-r_out, cy-r_out, cx+r_out, cy+r_out,
                         outline=col, width=2, fill="")

        # Inner dot
        r_dot = 6 + math.sin(t * 0.08) * 2
        self.create_oval(cx-r_dot, cy-r_dot, cx+r_dot, cy+r_dot,
                         fill=col, outline="")

        # State text below
        labels = {
            "idle": "STANDBY",
            "listening": "LISTENING",
            "thinking": "PROCESSING",
            "speaking": "SPEAKING",
            "speaking_llm": "RESPONDING",
        }
        self.create_text(cx, cy + 70, text=labels.get(self.state, ""),
                         fill=col, font=("Courier New", 8, "bold"))

    def _animate(self):
        self.t += 1
        self._draw()
        self.after(35, self._animate)


# ── SYSTEM GAUGE ──────────────────────────────────────────────────────────────
class Gauge(tk.Canvas):
    def __init__(self, parent, label="CPU", size=90, **kw):
        super().__init__(parent, width=size, height=size+16,
                         bg=PANEL2, highlightthickness=0, **kw)
        self.label = label
        self.size = size
        self.value = 0
        self._draw()

    def set_value(self, v):
        self.value = v
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self.size
        cx, cy = s/2, s/2 + 2
        r = s/2 - 8
        v = max(0, min(100, self.value))

        # Background arc
        self.create_arc(cx-r, cy-r, cx+r, cy+r,
                        start=140, extent=-280, style=tk.ARC,
                        outline=BORDER, width=6)

        # Value arc
        col = SUCCESS if v < 60 else WARN if v < 85 else DANGER
        extent = -280 * (v / 100)
        if abs(extent) > 1:
            self.create_arc(cx-r, cy-r, cx+r, cy+r,
                            start=140, extent=extent, style=tk.ARC,
                            outline=col, width=6)

        # Center value
        self.create_text(cx, cy, text=f"{int(v)}%",
                         fill=col, font=("Courier New", 12, "bold"))

        # Label
        self.create_text(cx, s+10, text=self.label,
                         fill=MUTED, font=("Courier New", 8))


# ── NEWS TICKER ───────────────────────────────────────────────────────────────
# ── FALLBACK headlines shown while fetching / if offline ─────────────────────
FALLBACK_NEWS = [
    "BHAILU ONLINE — ALL NEURAL PATHWAYS ACTIVE",
    "SECURITY PROTOCOLS UPDATED — ALL SYSTEMS NOMINAL",
    "GLOBAL NETWORK LATENCY: 12ms — OPTIMAL",
    "AI SUBSYSTEMS RUNNING AT 99.7% EFFICIENCY",
    "FETCHING LIVE INTELLIGENCE FEEDS...",
]

# RSS feeds — no API key needed, purely public
RSS_FEEDS = [
    ("BBC",     "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("REUTERS", "https://feeds.reuters.com/reuters/topNews"),
    ("TECHCR",  "https://techcrunch.com/feed/"),
    ("NASA",    "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
]

def fetch_live_news(max_items: int = 30) -> list[str]:
    """Pull headlines from RSS feeds. Returns list of uppercase strings."""
    try:
        import feedparser
    except ImportError:
        return FALLBACK_NEWS

    headlines = []
    for source, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                title = entry.get("title", "").strip()
                if title:
                    # Clean HTML entities and truncate
                    import html
                    title = html.unescape(title)
                    title = title[:120]
                    headlines.append(f"[{source}]  {title.upper()}")
        except Exception:
            continue

    random.shuffle(headlines)
    return headlines if headlines else FALLBACK_NEWS


class NewsTicker(tk.Canvas):
    def __init__(self, parent, width=800, **kw):
        super().__init__(parent, width=width, height=22,
                         bg=PANEL, highlightthickness=0, **kw)
        self.w = width
        self.headlines = list(FALLBACK_NEWS)
        self.text = "  ◈  ".join(self.headlines) + "  ◈  "
        self.x = float(width)
        self._draw()
        self._scroll()
        # Fetch real news in background — swap in when ready
        threading.Thread(target=self._load_news, daemon=True).start()
        # Refresh every 10 minutes
        self.after(600_000, self._refresh_news)

    def _load_news(self):
        live = fetch_live_news()
        self.headlines = live
        self.text = "  ◈  ".join(live) + "  ◈  "

    def _refresh_news(self):
        threading.Thread(target=self._load_news, daemon=True).start()
        self.after(600_000, self._refresh_news)

    def _draw(self):
        self.delete("all")
        self.create_text(int(self.x), 11, text=self.text, anchor="w",
                         fill=ACCENT3, font=("Courier New", 8))

    def _scroll(self):
        self.x -= 1.5
        if self.x < -len(self.text) * 5.5:
            self.x = float(self.w)
        self._draw()
        self.after(30, self._scroll)


# ── MAIN DASHBOARD ────────────────────────────────────────────────────────────
class BhailuDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BHAILU")
        self.geometry(f"{W}x{H}")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.status_var = tk.StringVar(value="INITIALIZING")
        self.ollama_ok = False
        self.bhailu_proc = None

        self._build_ui()
        self._start_bhailu()

    # ── UI BUILD ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        fn_title = tkfont.Font(family="Courier New", size=20, weight="bold")
        fn_sub   = tkfont.Font(family="Courier New", size=8)
        fn_stat  = tkfont.Font(family="Courier New", size=10, weight="bold")
        fn_log   = tkfont.Font(family="Courier New", size=9)
        fn_lbl   = tkfont.Font(family="Courier New", size=7)
        fn_btn   = tkfont.Font(family="Courier New", size=8, weight="bold")
        self._fn_log = fn_log
        self._fn_lbl = fn_lbl

        # ── TOP BAR ──────────────────────────────────────────────────────────
        top = tk.Frame(self, bg=PANEL, height=50)
        top.pack(fill=tk.X)
        top.pack_propagate(False)

        # Left: logo
        tk.Label(top, text="◈ BHAILU", font=fn_title,
                 fg=ACCENT, bg=PANEL).pack(side=tk.LEFT, padx=16, pady=8)
        tk.Label(top, text="BHAILU — YOUR PERSONAL AI ASSISTANT",
                 font=fn_sub, fg=MUTED, bg=PANEL).pack(side=tk.LEFT, padx=4)

        # Right: time + status
        self.time_var = tk.StringVar(value="")
        tk.Label(top, textvariable=self.time_var, font=fn_stat,
                 fg=ACCENT3, bg=PANEL).pack(side=tk.RIGHT, padx=16)
        self.status_label = tk.Label(top, textvariable=self.status_var,
                                     font=fn_stat, fg=ACCENT, bg=PANEL)
        self.status_label.pack(side=tk.RIGHT, padx=4)
        tk.Label(top, text="STATUS:", font=fn_lbl, fg=MUTED, bg=PANEL).pack(side=tk.RIGHT)

        self._tick_clock()

        # ── SEPARATOR ────────────────────────────────────────────────────────
        tk.Canvas(self, height=2, bg=ACCENT, highlightthickness=0).pack(fill=tk.X)

        # ── NEWS TICKER ──────────────────────────────────────────────────────
        self.ticker = NewsTicker(self, width=W)
        self.ticker.pack(fill=tk.X)

        # ── MAIN BODY ────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # LEFT column (voice ring + quick cmds)
        left = tk.Frame(body, bg=BG, width=180)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text="VOICE INTERFACE", font=fn_lbl,
                 fg=MUTED, bg=BG).pack(pady=(4,2))
        self.ring = VoiceRing(left, size=160)
        self.ring.pack(pady=4)

        # Ollama indicator
        self.ollama_var = tk.StringVar(value="● OLLAMA: CHECKING")
        self.ollama_lbl = tk.Label(left, textvariable=self.ollama_var,
                                   font=fn_lbl, fg=MUTED, bg=BG)
        self.ollama_lbl.pack()

        tk.Label(left, text="QUICK COMMANDS", font=fn_lbl,
                 fg=MUTED, bg=BG).pack(pady=(12,4))

        quick_cmds = [
            ("🕐 Time",          "what is the time"),
            ("📅 Date",          "what is today's date"),
            ("💻 System Stats",  "show system stats"),
            ("🔊 Volume 70",     "volume to 70"),
            ("🔇 Mute",          "mute"),
            ("🌐 Open Browser",  "open chrome"),
            ("🔍 Search News",   "search for latest tech news"),
        ]

        for label, cmd in quick_cmds:
            b = tk.Button(left, text=label, font=fn_btn,
                          bg=PANEL2, fg=ACCENT3,
                          activebackground=DIM, activeforeground=ACCENT,
                          relief=tk.FLAT, cursor="hand2", width=18, pady=3,
                          command=lambda c=cmd: self._inject(c))
            b.pack(fill=tk.X, padx=4, pady=1)
            b.bind("<Enter>", lambda e, w=b: w.configure(bg=DIM))
            b.bind("<Leave>", lambda e, w=b: w.configure(bg=PANEL2))

        # CENTRE column (map + log)
        centre = tk.Frame(body, bg=BG)
        centre.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)

        # World map
        map_frame = tk.Frame(centre, bg=PANEL, bd=1, relief=tk.FLAT,
                             highlightthickness=1, highlightbackground=BORDER)
        map_frame.pack(fill=tk.X)
        self.world_map = WorldMap(map_frame)
        self.world_map.pack()

        # Conversation log
        log_outer = tk.Frame(centre, bg=PANEL2)
        log_outer.pack(fill=tk.BOTH, expand=True, pady=(6,0))

        tk.Label(log_outer, text=" ◈ COMMUNICATION LOG", font=fn_lbl,
                 fg=MUTED, bg=PANEL2, anchor="w").pack(fill=tk.X, padx=6, pady=(4,2))

        scroll = tk.Scrollbar(log_outer, bg=PANEL2, troughcolor=BG,
                              relief=tk.FLAT, activebackground=ACCENT)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log = tk.Text(log_outer, font=fn_log, bg=PANEL2, fg=TEXT,
                           insertbackground=ACCENT, relief=tk.FLAT,
                           yscrollcommand=scroll.set, state=tk.DISABLED,
                           wrap=tk.WORD, pady=4, padx=8)
        self.log.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.log.yview)

        self.log.tag_config("bhailu", foreground=ACCENT2)
        self.log.tag_config("you",    foreground=SUCCESS)
        self.log.tag_config("status", foreground=MUTED)
        self.log.tag_config("warn",   foreground=WARN)
        self.log.tag_config("ts",     foreground=MUTED)

        # RIGHT column (gauges + info panels)
        right = tk.Frame(body, bg=BG, width=180)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        tk.Label(right, text="SYSTEM DIAGNOSTICS", font=fn_lbl,
                 fg=MUTED, bg=BG).pack(pady=(4,6))

        gauges_row = tk.Frame(right, bg=BG)
        gauges_row.pack()
        self.gauge_cpu = Gauge(gauges_row, "CPU", size=82)
        self.gauge_cpu.pack(side=tk.LEFT, padx=4)
        self.gauge_ram = Gauge(gauges_row, "RAM", size=82)
        self.gauge_ram.pack(side=tk.LEFT, padx=4)

        self.gauge_disk = Gauge(right, "DISK", size=82)
        self.gauge_disk.pack(pady=4)

        # Info panels
        tk.Label(right, text="NETWORK STATUS", font=fn_lbl,
                 fg=MUTED, bg=BG).pack(pady=(8,2))
        info_frame = tk.Frame(right, bg=PANEL2, padx=8, pady=6)
        info_frame.pack(fill=tk.X, padx=4)

        self.net_lines = []
        for row in [("OLLAMA", "localhost:11434"),
                    ("STT",    "Google API"),
                    ("TTS",    "LOCAL pyttsx3"),
                    ("LLM",    "llama3")]:
            r = tk.Frame(info_frame, bg=PANEL2)
            r.pack(fill=tk.X, pady=1)
            tk.Label(r, text=row[0]+":", font=fn_lbl, fg=MUTED, bg=PANEL2,
                     width=8, anchor="w").pack(side=tk.LEFT)
            lbl = tk.Label(r, text=row[1], font=fn_lbl, fg=ACCENT3, bg=PANEL2)
            lbl.pack(side=tk.LEFT)

        # Uptime
        self._start_time = time.time()
        self.uptime_var = tk.StringVar(value="UPTIME: 00:00:00")
        tk.Label(right, textvariable=self.uptime_var, font=fn_lbl,
                 fg=MUTED, bg=BG).pack(pady=(12,2))

        self._tick_uptime()

        # ── BOTTOM BAR ────────────────────────────────────────────────────────
        bottom = tk.Frame(self, bg=PANEL, height=36)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        bottom.pack_propagate(False)

        tk.Label(bottom, text="MANUAL INPUT:", font=fn_lbl,
                 fg=MUTED, bg=PANEL).pack(side=tk.LEFT, padx=(10,4), pady=6)

        self.cmd_var = tk.StringVar()
        entry = tk.Entry(bottom, textvariable=self.cmd_var,
                         font=fn_log, bg=BG, fg=TEXT,
                         insertbackground=ACCENT, relief=tk.FLAT,
                         selectbackground=DIM, width=50)
        entry.pack(side=tk.LEFT, padx=4, pady=6)
        entry.bind("<Return>", self._on_manual)

        tk.Button(bottom, text="EXECUTE ▶", font=fn_btn,
                  bg=DIM, fg=ACCENT, activebackground=ACCENT,
                  activeforeground=BG, relief=tk.FLAT, cursor="hand2",
                  command=self._on_manual).pack(side=tk.LEFT, padx=4)

        tk.Button(bottom, text="✕ SHUTDOWN", font=fn_btn,
                  bg=PANEL, fg=DANGER, activebackground=DANGER,
                  activeforeground=BG, relief=tk.FLAT, cursor="hand2",
                  command=self._quit).pack(side=tk.RIGHT, padx=10)

    # ── CLOCK & UPTIME ────────────────────────────────────────────────────────
    def _tick_clock(self):
        self.time_var.set(datetime.datetime.now().strftime("%H:%M:%S  |  %a %d %b"))
        self.after(1000, self._tick_clock)

    def _tick_uptime(self):
        elapsed = int(time.time() - self._start_time)
        h, r = divmod(elapsed, 3600)
        m, s = divmod(r, 60)
        self.uptime_var.set(f"UPTIME: {h:02d}:{m:02d}:{s:02d}")
        self.after(1000, self._tick_uptime)

    # ── LOGGING ───────────────────────────────────────────────────────────────
    def _log(self, text, tag="status"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, f"[{ts}] ", "ts")
        self.log.insert(tk.END, text + "\n", tag)
        self.log.configure(state=tk.DISABLED)
        self.log.see(tk.END)

    # ── STATUS UPDATE ─────────────────────────────────────────────────────────
    def _set_status(self, state: str):
        map_ = {
            "ready":        ("● ONLINE",      ACCENT,   "idle"),
            "listening":    ("◉ LISTENING",   SUCCESS,  "listening"),
            "processing":   ("⟳ PROCESSING",  WARN,     "thinking"),
            "thinking":     ("⟳ THINKING",    WARN,     "thinking"),
            "speaking":     ("◈ SPEAKING",    ACCENT,   "speaking"),
            "speaking_llm": ("◈ RESPONDING",  ACCENT2,  "speaking_llm"),
            "timeout":      ("○ WAITING",     MUTED,    "idle"),
            "error":        ("✕ ERROR",       DANGER,   "idle"),
            "stt_error":    ("✕ STT ERROR",   WARN,     "idle"),
        }
        label, color, ring_state = map_.get(state, ("● ONLINE", ACCENT, "idle"))
        self.status_var.set(label)
        self.status_label.configure(fg=color)
        self.ring.set_state(ring_state)

    # ── BHAILU PROCESS ────────────────────────────────────────────────────────
    def _start_bhailu(self):
        self._log("Initializing BHAILU subsystems...", "status")
        script = os.path.join(os.path.dirname(__file__), "bhailu_core.py")
        try:
            self.bhailu_proc = subprocess.Popen(
                [sys.executable, "-u", script],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            threading.Thread(target=self._read_proc, daemon=True).start()
        except Exception as e:
            self._log(f"Launch failed: {e}", "warn")
            self._set_status("error")

    def _read_proc(self):
        for line in self.bhailu_proc.stdout:
            line = line.strip()
            if line:
                self.after(0, self._handle_line, line)

    def _handle_line(self, line: str):
        if line.startswith("BHAILU: "):
            self._log("BHAILU ▶ " + line[8:], "bhailu")
            self._set_status("speaking")
            self.after(2500, lambda: self._set_status("ready"))
        elif line.startswith("YOU: "):
            self._log("YOU ▶ " + line[5:], "you")
        elif line.startswith("STATUS: "):
            s = line[8:]
            self._set_status(s)
            if s == "listening":
                self._log("Listening...", "status")
        elif line.startswith("STATS: "):
            try:
                stats = json.loads(line[7:])
                self.gauge_cpu.set_value(stats.get("cpu", 0))
                self.gauge_ram.set_value(stats.get("ram", 0))
                self.gauge_disk.set_value(stats.get("disk", 0))
                # Update Ollama indicator
                if not self.ollama_ok:
                    import requests as req
                    try:
                        req.get("http://localhost:11434/api/tags", timeout=1)
                        self.ollama_ok = True
                        self.ollama_var.set("● OLLAMA: ONLINE")
                        self.ollama_lbl.configure(fg=SUCCESS)
                    except:
                        self.ollama_var.set("○ OLLAMA: OFFLINE")
                        self.ollama_lbl.configure(fg=DANGER)
            except:
                pass
        else:
            self._log(line, "status")

    # ── COMMAND INJECTION ─────────────────────────────────────────────────────
    def _on_manual(self, event=None):
        cmd = self.cmd_var.get().strip()
        if not cmd:
            return
        self.cmd_var.set("")
        self._inject(cmd)

    def _inject(self, cmd: str):
        self._log(f"YOU ▶ {cmd}", "you")
        def _run():
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "bhailu_core", os.path.join(os.path.dirname(__file__), "bhailu_core.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            resp, _ = mod.route_command(cmd)
            self.after(0, lambda: self._log(f"BHAILU ▶ {resp}", "bhailu"))
            mod.speak(resp)
        threading.Thread(target=_run, daemon=True).start()

    # ── QUIT ──────────────────────────────────────────────────────────────────
    def _quit(self):
        if self.bhailu_proc:
            self.bhailu_proc.terminate()
        self.destroy()


if __name__ == "__main__":
    BhailuDashboard().mainloop()
