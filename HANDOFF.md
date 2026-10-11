# Handoff Documentation: Text-to-Audio Tool (`text-to-audio-tool`)

## 1. Executive Summary

`text-to-audio-tool` is a lightweight, low-latency text-to-speech utility bridging **Windows 11 host environments** and **WSL2 Linux**. It is triggered via a global Windows hotkey (`Ctrl + Alt + C`), captures clipboard contents via PowerShell interop, runs a custom deterministic regex text normalization pipeline to strip markdown artifacts and reformat technical tokens into natural spoken English, synthesizes speech using Microsoft Edge Neural TTS (`edge-tts`), and plays it hands-free via `mpv`.

---

## 2. Environment & System Details

- **Host OS**: Windows 11
- **Subsystem**: WSL2 (Ubuntu 24.04 LTS)
- **Repo Location (WSL2)**: `/home/giovanni/text-to-audio-tool`
- **Repo Location (Windows UNC)**: `\\wsl.localhost\Ubuntu\home\giovanni\text-to-audio-tool`
- **Python Runtime**: Python 3.12.3 in local virtual environment (`.venv/bin/python3`)
- **Core Dependencies**:
  - `edge-tts` (v7.2.8+)
  - `mpv` (installed via `apt`)
  - `powershell.exe` (invoked via WSL interop for Windows clipboard access)
- **Audio Output**: Uses WSLg / PulseAudio bridge to route sound through Windows default audio device.

---

## 3. Core Architecture & Workflow

1. **Trigger**:
   - User copies arbitrary text anywhere in Windows (`Ctrl + C`).
   - User invokes `Ctrl + Alt + C` (bound to Windows Desktop shortcut pointing to `read_clipboard.bat` or `read_speed.bat`).
2. **WSL Invocation**:
   - The batch script invokes `wsl.exe bash -ic "cd /home/giovanni/text-to-audio-tool && source .venv/bin/activate && python3 txt2audio.py -cl -p -r -20%"`.
3. **Clipboard Retrieval (`get_clipboard_text`)**:
   - Executes `powershell.exe -Command Get-Clipboard`.
   - Decodes output with fallback encoding order: `utf-8` $\rightarrow$ `cp850` $\rightarrow$ `windows-1252`.
4. **Speech Sanitization Pipeline (`clean_text_for_tts`)**:
   - **Markdown Headings**: Strips `#` hashes; rewrites `## 1. Title` into `Section 1. Title` and ensures sentence-ending pauses.
   - **Markdown Emphasis**: Unwraps `**bold**`, `*italic*`, `~~strikethrough~~` without speaking asterisks or tildes.
   - **Bullet Points**: Strips list markers (`*`, `-`, `+`, `•`) and guarantees sentence-ending periods between items.
   - **Code & Underscores**:
     - Strips backticks.
     - Replaces all remaining underscores (`_`) with spaces to prevent Jenny from saying *"underscore"*.
     - Transforms function calls like `foo_bar(arg)` to `foo bar of arg`, and `func()` to `func`.
   - **URLs & Links**:
     - `[label](url)` preserves `label`.
     - Raw URLs are converted to speakable tokens (`https github com ...`).
   - **Filesystem Paths**:
     - Unix paths (`/home/user/repo`) $\rightarrow$ `forward slash home forward slash user forward slash repo`.
     - Windows paths (`C:\dir\file`) $\rightarrow$ `C drive backslash dir backslash file`.
   - **Math & Arrows**:
     - `$\rightarrow$`, `->`, `→` $\rightarrow$ `"pointing to"`.
     - `&` $\rightarrow$ `"and"`.
5. **Speech Synthesis & Playback**:
   - Async call to `edge_tts.Communicate(text, voice, rate)`.
   - Saves to `clipboard_audio.mp3`.
   - Spawns `mpv --no-terminal clipboard_audio.mp3`.

---

## 4. Key Files Manifest

| File | Purpose |
| :--- | :--- |
| `txt2audio.py` | Main CLI entrypoint, text normalizer, TTS generator, and audio player caller. |
| `read_clipboard.bat` | Non-interactive Windows batch script configured for 1-click hotkey execution (`Ctrl + Alt + C`). |
| `read_speed.bat` | Interactive Windows batch script prompting user for custom playback speed percentage. |
| `requirements.txt` | Python package specifications (`edge-tts`). |
| `.gitignore` | Ignores virtual environments, audio files (`*.mp3`), and Python bytecode caches. |
| `README.md` | Public-facing documentation, architecture, and step-by-step hotkey setup guide. |
| `HANDOFF.md` | This technical relay file for future developers and AI agents. |

---

## 5. CLI Reference (`txt2audio.py`)

```
usage: txt2audio.py [-h] [-i INPUT_FILE] [-cl] [-o OUTPUT] [-v VOICE] [-r RATE] [-p] [--no-clean]

options:
  -h, --help            Show help message and exit
  -i, --input_file      Path to input text or markdown file
  -cl, --clipboard      Read text from Windows clipboard via powershell.exe
  -o, --output          Output MP3 filename (default: clipboard_audio.mp3)
  -v, --voice           Edge-TTS neural voice (default: en-US-JennyNeural)
  -r, --rate            Speech speed offset (e.g. -20%, +10%)
  -p, --play            Play audio immediately after generation using mpv
  --no-clean            Disable markdown and text sanitization (raw TTS)
```

---

## 6. How to Verify Working State

To verify functionality after cloning or transferring:

```bash
cd /home/giovanni/text-to-audio-tool
source .venv/bin/activate

# 1. Run direct test with markdown and code snippets
python3 -c "from txt2audio import clean_text_for_tts; print(clean_text_for_tts('## 1. Test\n* **item**: clean_text_for_tts(text) -> /home/user'))"
# Expected output:
# Section 1. Test
# item: clean text for tts of text pointing to forward slash home forward slash user.

# 2. Test audio generation
python3 txt2audio.py -cl -p -r -20%
```

---

## 7. Future Roadmap & Opportunities for Next Agent

1. **Streaming Audio Playback**:
   - Currently, the script awaits the full MP3 before spawning `mpv`.
   - Could be refactored to pipe `edge_tts.Communicate.stream()` directly into `mpv -` via `stdin` for sub-second first-byte speech response on long texts.
2. **System Tray / Background Resident Daemon**:
   - Implement an optional background daemon (e.g. Python `pystray` or lightweight Windows AutoHotkey script) to intercept hotkeys without launching a console process.
3. **Voice Auto-Switching / Language Detection**:
   - Use `langdetect` to automatically switch between English neural voices (`en-US-JennyNeural`) and Spanish/Italian voices based on clipboard language.
