# ◈ BHAILU — Your Personal AI Assistant

A local AI assistant with a dark HUD dashboard. Powered by Ollama (runs 100% offline).

## 🚀 Quick Start

### Step 1 — Install Ollama (one time)
- Download from: https://ollama.com
- Then run: `ollama pull llama3`
- Start it: `ollama serve`

### Step 2 — Launch BHAILU
**Windows:** Double-click `start_bhailu.bat`
**Mac/Linux:** `./start_bhailu.sh`
**Manual:** `pip install -r requirements.txt` → `python bhailu_dashboard.py`

## 🎙️ Voice Commands
| Say | Action |
|-----|--------|
| *Anything* | BHAILU answers via LLM (Ollama) |
| "What's the time?" | Fast local response |
| "Open Chrome" | Opens app |
| "Volume to 70" | Sets volume |
| "System stats" | CPU/RAM/Disk |
| "Search for X" | Opens browser |
| "Goodbye Bhailu" | Exits |

## 📁 Files
- `bhailu_core.py` — AI brain (Ollama + voice + commands)
- `bhailu_dashboard.py` — Dark HUD interface
- `start_bhailu.bat` — Windows launcher
- `start_bhailu.sh` — Mac/Linux launcher
