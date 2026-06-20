"""
BHAILU Core — Bhailu — Your Personal AI Assistant
Powered by Ollama (local LLM) + pyttsx3 TTS + SpeechRecognition STT
"""

import speech_recognition as sr
import pyttsx3
import requests
import json
import datetime
import os
import platform
import subprocess
import webbrowser
import random
import threading
import sys
import re
import time
import psutil

SYSTEM = platform.system()
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"  # change to "mistral" or "phi3" if preferred

# ── BHAILU PERSONALITY PROMPT ────────────────────────────────────────────────
SYSTEM_PROMPT = """You are BHAILU (Bhailu — Your Personal AI Assistant), 
a sharp, witty, confident AI assistant. You are slightly sarcastic but always helpful. Your name is Bhailu.
You speak concisely (1-3 sentences max unless explaining something complex).
You call the user "Boss" occasionally. You have a dry sense of humor.
You are running locally on the user's machine — no cloud, no internet needed for your brain.
Never break character. Never say you are an AI made by Meta/Ollama — you are BHAILU
Current time: {time}. Current date: {date}."""

# ── TTS ENGINE ────────────────────────────────────────────────────────────────
engine = pyttsx3.init()
engine.setProperty("rate", 165)
engine.setProperty("volume", 1.0)

# Pick a female voice
voices = engine.getProperty("voices")
female_voice = None
for v in voices:
    name = v.name.lower()
    if any(w in name for w in ["female", "zira", "samantha", "victoria", "karen", "moira", "fiona", "susan", "hazel"]):
        female_voice = v.id
        break
if not female_voice and len(voices) > 1:
    female_voice = voices[1].id  # index 1 is often female on Windows
if female_voice:
    engine.setProperty("voice", female_voice)

_tts_lock = threading.Lock()

def speak(text: str):
    print(f"BHAILU: {text}", flush=True)
    with _tts_lock:
        engine.say(text)
        engine.runAndWait()

# ── OLLAMA LLM ────────────────────────────────────────────────────────────────
conversation_history = []

def ask_bhailu(user_input: str) -> str:
    """Send message to local Ollama and get BHAILU's response."""
    now = datetime.datetime.now()
    system = SYSTEM_PROMPT.format(
        time=now.strftime("%I:%M %p"),
        date=now.strftime("%A, %B %d %Y")
    )

    conversation_history.append({"role": "user", "content": user_input})

    # Build prompt with history (last 6 turns to save memory)
    history_text = ""
    for msg in conversation_history[-6:]:
        role = "User" if msg["role"] == "user" else "BHAILU"
        history_text += f"{role}: {msg['content']}\n"

    full_prompt = f"{system}\n\nConversation:\n{history_text}BHAILU:"

    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 200}
        }, timeout=30)
        if resp.status_code == 200:
            reply = resp.json().get("response", "").strip()
            # Clean up any "BHAILU:" prefix the model might add
            reply = re.sub(r"^(BHAILU:|F\.R\.I\.D\.A\.Y\.:)\s*", "", reply).strip()
            conversation_history.append({"role": "assistant", "content": reply})
            return reply
        else:
            return "I'm having trouble reaching my brain right now, Boss. Is Ollama running?"
    except requests.exceptions.ConnectionError:
        return offline_reply(user_input)
    except requests.exceptions.Timeout:
        return offline_reply(user_input)
    except Exception as e:
        return offline_reply(user_input)


OFFLINE_REPLIES = {
    "greeting":  ["Good morning, Boss! Bhailu is online and ready.",
                  "Hello Boss! How can I assist you today?",
                  "Hey there, Boss! What do you need?"],
    "how_are":   ["Running at full capacity, Boss. All systems nominal.",
                  "Perfectly operational, Boss. Ready for your commands."],
    "thanks":    ["Anytime, Boss.", "Happy to help, Boss.", "Of course, Boss."],
    "joke":      ["Why don't scientists trust atoms? Because they make up everything.",
                  "Why do programmers prefer dark mode? Because light attracts bugs.",
                  "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads."],
    "default":   ["Ollama isn't running, Boss. Start it with: ollama serve — then I'll be fully operational.",
                  "My AI brain is offline. Run 'ollama serve' to activate it, Boss.",
                  "I can handle basic commands right now. For full AI chat, start Ollama first, Boss."],
}

def offline_reply(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["hello", "hi", "hey", "good morning", "good evening", "good afternoon", "morning"]):
        return random.choice(OFFLINE_REPLIES["greeting"])
    if any(w in t for w in ["how are you", "how are u", "you doing"]):
        return random.choice(OFFLINE_REPLIES["how_are"])
    if any(w in t for w in ["thank", "thanks", "cheers"]):
        return random.choice(OFFLINE_REPLIES["thanks"])
    if any(w in t for w in ["joke", "funny", "laugh"]):
        return random.choice(OFFLINE_REPLIES["joke"])
    return random.choice(OFFLINE_REPLIES["default"])

def check_ollama() -> bool:
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except:
        return False

# ── SYSTEM COMMANDS ────────────────────────────────────────────────────────────
def get_system_stats() -> dict:
    return {
        "cpu": psutil.cpu_percent(interval=0.1),
        "ram": psutil.virtual_memory().percent,
        "ram_used": round(psutil.virtual_memory().used / (1024**3), 1),
        "ram_total": round(psutil.virtual_memory().total / (1024**3), 1),
        "disk": psutil.disk_usage("/").percent,
    }

def set_volume(level: int) -> str:
    level = max(0, min(100, level))
    if SYSTEM == "Windows":
        # No nircmd needed — pure PowerShell via Windows Audio API
        try:
            ps_cmd = (
                "Add-Type -TypeDefinition @'\n"
                "using System.Runtime.InteropServices;\n"
                "using System;\n"
                "[ComImport, Guid(\"BCDE0395-E52F-467C-8E3D-C4579291692E\")]\n"
                "class MMDeviceEnumerator {}\n"
                "'@ -ErrorAction SilentlyContinue 2>$null;\n"
                "try {\n"
                "  $vol = New-Object -ComObject WScript.Shell;\n"
                f"  $level = {level};\n"
                # Send VK_VOLUME_DOWN 50 times to reset, then VK_VOLUME_UP to target
                "  1..50 | % { $vol.SendKeys([char]174) };\n"
                f"  1..([int]($level/2)) | % {{ $vol.SendKeys([char]175) }}\n"
                "} catch {}"
            )
            subprocess.Popen(
                ["powershell", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass
    elif SYSTEM == "Darwin":
        subprocess.Popen(["osascript", "-e", f"set volume output volume {level}"])
    else:
        subprocess.Popen(["amixer", "-q", "sset", "Master", f"{level}%"])
    return f"Volume set to {level} percent, Boss."

def _win_launch(exe_name: str) -> bool:
    """Try to launch an exe on Windows by searching common install paths."""
    import glob
    # 1. Try direct shell launch (works if exe is on PATH)
    try:
        subprocess.Popen(f'start "" "{exe_name}"', shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        pass
    # 2. Search common install directories
    search_dirs = [
        os.path.expandvars(r"%ProgramFiles%"),
        os.path.expandvars(r"%ProgramFiles(x86)%"),
        os.path.expandvars(r"%LocalAppData%"),
        os.path.expandvars(r"%AppData%"),
        os.path.expandvars(r"%LocalAppData%\Programs"),
    ]
    for d in search_dirs:
        matches = glob.glob(os.path.join(d, "**", exe_name), recursive=True)
        if matches:
            subprocess.Popen([matches[0]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    return False


def open_app(app: str) -> str:
    original = app
    app = app.lower().strip()

    # ── Normalise speech → canonical key ─────────────────────────────────────
    ALIASES = {
        # Browsers
        "browser": "chrome", "web browser": "chrome", "internet": "chrome",
        "internet browser": "chrome", "web": "chrome",
        "google chrome": "chrome", "google": "chrome",
        "brave browser": "brave", "brave": "brave",
        "edge browser": "edge", "microsoft edge": "edge",
        "opera browser": "opera",
        # Common apps
        "music": "spotify", "music player": "spotify",
        "code editor": "vscode", "editor": "vscode", "vs code": "vscode", "visual studio code": "vscode",
        "file manager": "explorer", "files": "explorer", "my files": "explorer",
        "command prompt": "cmd", "command line": "cmd", "console": "cmd", "terminal": "cmd",
        "paint": "mspaint", "text editor": "notepad",
        "word": "winword", "ms word": "winword",
        "excel": "excel", "ms excel": "excel",
        "powerpoint": "powerpnt", "ms powerpoint": "powerpnt",
        "mail": "outlook", "email": "outlook", "ms outlook": "outlook",
        "task manager": "taskmgr",
        "whatsapp": "whatsapp", "telegram": "telegram",
        "zoom": "zoom", "teams": "teams", "microsoft teams": "teams",
        "photos": "photos", "camera": "camera",
    }
    app = ALIASES.get(app, app)

    # ── Windows ───────────────────────────────────────────────────────────────
    if SYSTEM == "Windows":
        # Built-in system commands (always on PATH)
        BUILTIN = {
            "notepad": "notepad", "calc": "calc", "calculator": "calc",
            "mspaint": "mspaint", "explorer": "explorer", "cmd": "cmd",
            "taskmgr": "taskmgr", "winword": "winword", "excel": "excel",
            "powerpnt": "powerpnt", "outlook": "outlook",
        }
        if app in BUILTIN:
            subprocess.Popen(BUILTIN[app], shell=True)
            return f"Opening {original}, Boss."

        # Apps that use 'start' with their registered name (in Windows registry)
        START_CMDS = {
            "photos":  "start ms-photos:",
            "camera":  "start microsoft.windows.camera:",
            "store":   "start ms-windows-store:",
            "settings": "start ms-settings:",
        }
        if app in START_CMDS:
            subprocess.Popen(START_CMDS[app], shell=True)
            return f"Opening {original}, Boss."

        # Exe names to search for in Program Files
        EXE_MAP = {
            "chrome":   "chrome.exe",
            "brave":    "brave.exe",
            "firefox":  "firefox.exe",
            "edge":     "msedge.exe",
            "opera":    "opera.exe",
            "spotify":  "Spotify.exe",
            "discord":  "Discord.exe",
            "vscode":   "Code.exe",
            "vlc":      "vlc.exe",
            "zoom":     "Zoom.exe",
            "teams":    "Teams.exe",
            "telegram": "Telegram.exe",
            "whatsapp": "WhatsApp.exe",
            "obs":      "obs64.exe",
            "steam":    "steam.exe",
        }
        exe = EXE_MAP.get(app)
        if exe:
            if _win_launch(exe):
                return f"Opening {original}, Boss."
            # Last resort: try 'start' with the exe name anyway
            subprocess.Popen(f'start "" "{exe}"', shell=True)
            return f"Launching {original}, Boss — if it's installed."

        # Unknown app — try running directly
        subprocess.Popen(f'start "" "{app}"', shell=True)
        return f"Attempting to open {original}, Boss."

    # ── macOS ─────────────────────────────────────────────────────────────────
    elif SYSTEM == "Darwin":
        MAC = {
            "chrome": "Google Chrome", "brave": "Brave Browser",
            "safari": "Safari", "firefox": "Firefox", "edge": "Microsoft Edge",
            "terminal": "Terminal", "finder": "Finder", "calculator": "Calculator",
            "spotify": "Spotify", "vlc": "VLC", "vscode": "Visual Studio Code",
            "discord": "Discord", "outlook": "Microsoft Outlook",
            "zoom": "zoom.us", "teams": "Microsoft Teams",
            "telegram": "Telegram", "whatsapp": "WhatsApp",
        }
        name = MAC.get(app, original)
        subprocess.Popen(["open", "-a", name])
        return f"Opening {original}, Boss."

    # ── Linux ─────────────────────────────────────────────────────────────────
    else:
        LIN = {
            "chrome": "google-chrome", "brave": "brave-browser",
            "firefox": "firefox", "edge": "microsoft-edge",
            "explorer": "nautilus", "files": "nautilus",
            "spotify": "spotify", "vlc": "vlc", "vscode": "code",
            "discord": "discord", "zoom": "zoom", "teams": "teams",
            "telegram": "telegram-desktop", "terminal": "gnome-terminal",
        }
        cmd = LIN.get(app, app)
        try:
            subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opening {original}, Boss."
        except FileNotFoundError:
            return f"Couldn't find {original} on your system, Boss."

# ── COMMAND ROUTER ─────────────────────────────────────────────────────────────
def route_command(text: str) -> tuple[str, bool]:
    """
    Returns (response, used_llm).
    Fast local commands bypass Ollama for speed.
    """
    t = text.lower().strip()

    # Time / date
    if re.search(r"\btime\b", t) and "date" not in t:
        r = datetime.datetime.now().strftime("It's %I:%M %p, Boss.")
        return r, False

    if re.search(r"\bdate\b|\bday is it\b|\btoday\b", t):
        r = datetime.datetime.now().strftime("Today is %A, %B %d %Y.")
        return r, False

    # Volume
    m = re.search(r"volume\s*(to|at)?\s*(\d+)", t)
    if m:
        return set_volume(int(m.group(2))), False
    if "mute" in t:
        return set_volume(0), False
    if "max volume" in t or "full volume" in t:
        return set_volume(100), False

    # Open app — handle "open X", "can you open X", "please open X", "launch X", "start X"
    m = re.search(r"(?:can you\s+|please\s+|could you\s+)?(?:open|launch|start|run)\s+(.+)", t)
    if m:
        app_name = m.group(1).strip()
        # Strip trailing filler like "for me", "please", "now"
        app_name = re.sub(r"\s*(for me|please|now|up)$", "", app_name).strip()
        return open_app(app_name), False

    # Search
    for phrase in ["search for", "search", "look up", "google"]:
        if phrase in t:
            q = t.split(phrase, 1)[-1].strip()
            webbrowser.open(f"https://duckduckgo.com/?q={q.replace(' ', '+')}")
            return f"Searching for {q}, Boss.", False

    # System stats
    if any(w in t for w in ["cpu", "ram", "memory", "disk", "system stats"]):
        s = get_system_stats()
        return f"CPU at {s['cpu']}%, RAM at {s['ram']}% ({s['ram_used']}GB of {s['ram_total']}GB).", False

    # Goodbye
    if any(w in t for w in ["goodbye", "bye", "shut down bhailu", "exit bhailu", "quit"]):
        speak("Powering down. Stay brilliant, Boss.")
        sys.exit(0)

    # Greetings & small talk — fast local, no LLM needed
    if any(w in t for w in ["hello", "hi bhailu", "hey bhailu", "good morning", "good evening", "good afternoon", "morning bhailu"]):
        h = datetime.datetime.now().hour
        if h < 12:   greeting = "Good morning, Boss!"
        elif h < 17: greeting = "Good afternoon, Boss!"
        else:        greeting = "Good evening, Boss!"
        return random.choice([
            f"{greeting} Bhailu is fully online.",
            f"{greeting} All systems operational. How can I assist?",
            f"{greeting} Ready for your commands.",
        ]), False

    if any(w in t for w in ["how are you", "how are u", "you okay", "you good"]):
        return random.choice([
            "Running at peak efficiency, Boss. All systems nominal.",
            "Perfectly operational, Boss. Better than ever.",
            "All diagnostics green, Boss. Never better.",
        ]), False

    if any(w in t for w in ["thank you", "thanks", "thank u", "cheers"]):
        return random.choice([
            "Anytime, Boss.", "Happy to help, Boss.", "Of course, Boss.", "Always, Boss."
        ]), False

    if any(w in t for w in ["joke", "funny", "make me laugh", "tell me a joke"]):
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything.",
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "Why did the computer go to the doctor? It had a virus.",
            "I asked my AI to tell me a joke. It said: I would, but I'm still processing your last request.",
        ]
        return random.choice(jokes), False

    # Everything else → LLM
    return ask_bhailu(text), True

# ── SPEECH RECOGNITION ────────────────────────────────────────────────────────
recognizer = sr.Recognizer()
recognizer.pause_threshold = 0.8
recognizer.energy_threshold = 300

def listen() -> str | None:
    with sr.Microphone() as source:
        print("STATUS: listening", flush=True)
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=12)
            print("STATUS: processing", flush=True)
            text = recognizer.recognize_google(audio)
            print(f"YOU: {text}", flush=True)
            return text
        except sr.WaitTimeoutError:
            print("STATUS: timeout", flush=True)
            return None
        except sr.UnknownValueError:
            print("STATUS: unclear", flush=True)
            return None
        except sr.RequestError:
            print("STATUS: stt_error", flush=True)
            return None

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
def main():
    # Check Ollama
    if check_ollama():
        speak("BHAILU online. All neural pathways active. How can I help, Boss?")
    else:
        speak("BHAILU online — but Ollama isn't running. Start it with: ollama serve. I'll handle basic commands for now.")

    print("STATUS: ready", flush=True)

    # Stream system stats every 5s
    def stats_loop():
        while True:
            s = get_system_stats()
            print(f"STATS: {json.dumps(s)}", flush=True)
            time.sleep(5)
    threading.Thread(target=stats_loop, daemon=True).start()

    while True:
        cmd = listen()
        if cmd:
            print("STATUS: thinking", flush=True)
            response, used_llm = route_command(cmd)
            if used_llm:
                print("STATUS: speaking_llm", flush=True)
            else:
                print("STATUS: speaking", flush=True)
            speak(response)
        print("STATUS: ready", flush=True)

if __name__ == "__main__":
    main()
