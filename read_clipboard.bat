@echo off
:: Direct 1-click clipboard TTS runner (ideal for global Windows hotkeys like Ctrl+Alt+C)
wsl.exe bash -ic "cd /home/giovanni/text-to-audio-tool && source .venv/bin/activate && python3 txt2audio.py -cl -p -r -20%%"
