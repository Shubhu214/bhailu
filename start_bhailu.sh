#!/bin/bash
echo "============================================"
echo "  B H A I L U  — AI Assistant"
echo "============================================"
[[ "$OSTYPE" == "linux-gnu"* ]] && sudo apt-get install -y portaudio19-dev espeak 2>/dev/null || true
[[ "$OSTYPE" == "darwin"* ]] && brew install portaudio 2>/dev/null || true
pip3 install -r requirements.txt --quiet
echo "Launching BHAILU..."
python3 bhailu_dashboard.py
