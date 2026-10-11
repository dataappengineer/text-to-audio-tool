@echo off
set /p speed="Enter speed adjustment (e.g., -20%% for slower, +10%% for faster, or just press Enter for -20%%): "
if "%speed%"=="" set speed=-20%%
if not "%speed:~-1%"=="%%" set speed=%speed%%%
wsl.exe bash -ic "cd /home/giovanni/text-to-audio-tool && source .venv/bin/activate && python3 txt2audio.py -cl -p -r %speed%"
