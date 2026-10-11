# 🎙️ Text-to-Audio Tool (WSL2 + Windows Clipboard TTS)

An intelligent, low-latency text-to-speech (TTS) automation tool built for developers, researchers, and power users working in Windows and WSL2. With a single global shortcut (**`Ctrl + Alt + C`**), it grabs whatever text you have highlighted or copied to your clipboard—cleans raw Markdown, symbols, code identifiers, and URLs into natural human phrasing—and speaks it aloud immediately using Microsoft Edge's neural voices.

---

## 🌟 Why This Exists

When copying answers from AI models (Gemini, ChatGPT, Claude) or technical documentation, standard text-to-speech engines struggle:
- They say *"asterisk asterisk bold asterisk asterisk"*.
- They recite raw links like *"h-t-t-p-s colon slash slash github dot com slash..."*.
- They read code identifiers as *"clean underscore text underscore for underscore tts open parenthesis text close parenthesis"*.
- They stumble on headings (`#`), list dashes (`-`), and horizontal dividers (`---`).

This tool introduces a deterministic **speech-normalization pipeline** in pure Python that converts unstructured technical text into fluent, human-like speech with zero external LLM latency.

---

## ✨ Features

- **⚡ Zero-Latency Markdown Sanitizer**:
  - **No more asterisk/hash spam**: Automatically unwraps `**bold**`, `*italic*`, `~~strikethrough~~`, `# headings`, and `---` dividers.
  - **Natural Code Reading**: Converts `snake_case` and function calls (e.g. `clean_text_for_tts(text)`) into spoken natural English (*"clean text for tts of text"*).
  - **Phonetic URLs**: Transforms complex web links into clean, speakable tokens without choking on slashes or query parameters.
  - **Spoken Filesystem Paths**: Pronounces paths cleanly (e.g. `/home/user/project` $\rightarrow$ *"forward slash home forward slash user forward slash project"*).
  - **Smart Pausing**: Automatically adds sentence pauses after headers and bullet points for natural breathing rhythm.
  - **Math & Arrows**: Translates `$\rightarrow$`, `->`, and `==>` into conversational phrases like *"pointing to"* or *"implies"*.
- **🎧 High-Quality Neural Voices**: Powered by `edge-tts` using Microsoft's neural models (default: `en-US-JennyNeural`, with options like `en-US-GuyNeural` or `en-GB-SoniaNeural`).
- **🪟 Seamless Windows $\leftrightarrow$ WSL2 Interop**: Transparently queries the Windows clipboard from within WSL via PowerShell interop without needing any local background servers.
- **🎵 Instant Playback**: Plays generated audio instantly via lightweight `mpv` player.

---

## 🏗️ Architecture

```
┌─────────────────────────┐
│ Windows Clipboard       │ (Ctrl + C from browser, IDE, or chat)
└────────────┬────────────┘
             │
      [Ctrl + Alt + C] (Windows Global Shortcut)
             │
             ▼
┌─────────────────────────┐
│ Windows Batch Runner    │ (read_clipboard.bat / read_speed.bat)
└────────────┬────────────┘
             │ wsl.exe bash -ic
             ▼
┌─────────────────────────┐
│ PowerShell Interop      │ (Fetches UTF-8 clipboard content)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Speech Normalizer (Py)  │ (Strips markdown, normalizes code/paths/URLs)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Edge-TTS Neural Engine  │ (Generates high-fidelity MP3)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ mpv Media Player        │ (Instant hands-free audio playback)
└─────────────────────────┘
```

---

## 🚀 Quick Start & Installation

### 1. Prerequisites (Inside WSL2)

Ensure you have Python 3.10+ and `mpv` installed in your WSL distribution (Ubuntu / Debian):

```bash
sudo apt update
sudo apt install -y python3 python3-venv mpv
```

### 2. Clone & Setup Virtual Environment

```bash
cd ~
git clone https://github.com/dataappengineer/text-to-audio-tool.git
cd text-to-audio-tool

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## ⌨️ Configuring the Windows Global Shortcut (`Ctrl + Alt + C`)

You can trigger speech instantly from anywhere in Windows with a single hotkey:

### Step 1: Locate the Batch File
Open Windows File Explorer and navigate to your WSL project folder:
```
\\wsl.localhost\Ubuntu\home\<your-username>\text-to-audio-tool
```
You will see two batch scripts:
- **`read_clipboard.bat`**: Instant 1-click playback at standard speed (-20%). Recommended for hotkeys.
- **`read_speed.bat`**: Prompts you in a terminal window for custom speed before playback.

### Step 2: Create a Windows Desktop Shortcut
1. Right-click on **`read_clipboard.bat`** $\rightarrow$ **Show more options** $\rightarrow$ **Send to** $\rightarrow$ **Desktop (create shortcut)**.
2. Go to your Windows Desktop and find the newly created shortcut.
3. Rename it to something clean, like `Read Clipboard TTS`.

### Step 3: Assign the Hotkey (`Ctrl + Alt + C`)
1. Right-click your new Desktop shortcut $\rightarrow$ select **Properties**.
2. Click into the **Shortcut key** field.
3. Press **`Ctrl + Alt + C`** on your keyboard (Windows will automatically register `Ctrl + Alt + C`).
4. *(Optional)* Set **Run:** to `Minimized` if you want the launch window to stay unobtrusive.
5. Click **Apply** and **OK**.

### Step 4: Test It Out!
1. Highlight any text in your browser, VS Code, or an AI chat, and press `Ctrl + C`.
2. Press **`Ctrl + Alt + C`**.
3. Within 1-2 seconds, the neural voice will read your text out loud!

---

## 🛠️ CLI Usage & Options

You can also run the tool manually from the command line in WSL or Windows:

```bash
# Read from clipboard with playback
python3 txt2audio.py -cl -p

# Read from a file and save to MP3
python3 txt2audio.py -i notes.md -o notes.mp3 -p

# Custom voice and speech speed
python3 txt2audio.py -cl -p -v en-US-GuyNeural -r +10%

# Disable text cleaning (raw TTS)
python3 txt2audio.py -cl -p --no-clean
```

### Command-line Arguments

| Flag | Description | Default |
| :--- | :--- | :--- |
| `-cl`, `--clipboard` | Read directly from Windows clipboard | `False` |
| `-i`, `--input_file` | Path to input text/markdown file | `None` |
| `-o`, `--output` | Destination `.mp3` file name | `clipboard_audio.mp3` |
| `-v`, `--voice` | Voice ID (e.g. `en-US-JennyNeural`, `en-US-GuyNeural`) | `en-US-JennyNeural` |
| `-r`, `--rate` | Speech speed rate (e.g. `-20%`, `+10%`) | `+0%` |
| `-p`, `--play` | Play audio immediately using `mpv` | `False` |
| `--no-clean` | Bypass markdown and text normalization | `False` |

---

## 📁 Repository Structure

```
.
├── txt2audio.py          # Core Python CLI, text sanitizer & Edge-TTS engine
├── read_clipboard.bat    # Windows 1-click batch runner (ideal for shortcuts)
├── read_speed.bat        # Interactive batch runner prompting for rate
├── requirements.txt      # Python dependencies
├── .gitignore            # Git exclusion rules (venv, audio outputs, caches)
├── HANDOFF.md            # Technical handoff document for AI agents / developers
└── README.md             # Project documentation & setup guide
```

---

## 📄 License

MIT License. Free to use, modify, and distribute.
