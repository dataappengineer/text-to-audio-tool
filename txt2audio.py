#!/usr/bin/env python3

import argparse
import asyncio
import edge_tts
import edge_tts.constants
import edge_tts.communicate
import os
import re
import sys
import subprocess

# Microsoft deprecated speech.platform.bing.com; redirect to working Edge TTS endpoint
_NEW_WSS_URL = (
    "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
    f"?Ocp-Apim-Subscription-Key={edge_tts.constants.TRUSTED_CLIENT_TOKEN}"
)
edge_tts.constants.WSS_URL = _NEW_WSS_URL
edge_tts.communicate.WSS_URL = _NEW_WSS_URL

def clean_text_for_tts(text: str) -> str:
    """
    Cleans and normalizes text for natural-sounding Text-To-Speech (TTS):
    - Strips markdown formatting (headers, bold, italics, bullets, blockquotes)
    - Replaces URLs with phonetic pronunciations
    - Cleans inline code and converts kebab-case / snake_case identifiers
    - Pronounces Unix / Windows file paths cleanly (e.g. 'forward slash home ...')
    - Replaces symbols like ->, $, & with natural spoken words
    - Normalizes pauses with proper punctuation at the end of headings and list items
    """
    if not text:
        return ""

    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove markdown code block fences (```python ... ``` -> keeps code or cleans)
    text = re.sub(r'```[a-zA-Z0-9_\-\.]*\n?', '', text)

    # Replace ampersands with "and" for natural speech
    text = re.sub(r'(?<=\S)\s*&\s*(?=\S)', ' and ', text)

    # Arrows and LaTeX / math transformations
    text = re.sub(r'\$\s*\\(?:rightarrow|to)\s*\$|\\(?:rightarrow|to)|-->|->|→', ' pointing to ', text)
    text = re.sub(r'<--|<-|←', ' pointing from ', text)
    text = re.sub(r'<==>|<=>|↔', ' equivalent to ', text)
    text = re.sub(r'==>|=>|⇒', ' implies ', text)

    # Strip math delimiters ($ and $$)
    text = re.sub(r'\${1,2}', '', text)

    # Clean phonetic URLs
    def clean_url(url: str) -> str:
        u = re.sub(r'^https?://', 'https ', url, flags=re.IGNORECASE)
        u = re.sub(r'www\.', 'www ', u, flags=re.IGNORECASE)
        u = re.sub(r'[/.\-_#?=&+:]+', ' ', u)
        return u.strip()

    # Markdown links: [label](url)
    def replace_markdown_link(match):
        label = match.group(1).strip()
        url = match.group(2).strip()
        if re.match(r'^https?://', label, re.IGNORECASE):
            return clean_url(label)
        return label

    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_markdown_link, text)

    # Clean standalone URLs
    text = re.sub(r'https?://[^\s)\]>]+', lambda m: clean_url(m.group(0)), text, flags=re.IGNORECASE)

    # Unix file paths: /home/giovanni/infra-lab
    def replace_unix_path(match):
        path = match.group(0)
        parts = [p for p in path.split('/') if p]
        cleaned_parts = [re.sub(r'[-_]', ' ', p) for p in parts]
        return 'forward slash ' + ' forward slash '.join(cleaned_parts)

    text = re.sub(r'(?<![a-zA-Z0-9_])/(?:[a-zA-Z0-9_.\-]+/)+[a-zA-Z0-9_.\-]+(?![a-zA-Z0-9_])', replace_unix_path, text)

    # Windows file paths: C:\Users\name\...
    def replace_win_path(match):
        path = match.group(0)
        drive = match.group(1)
        rest = match.group(2)
        parts = [p for p in rest.split('\\') if p]
        cleaned_parts = [re.sub(r'[-_]', ' ', p) for p in parts]
        return f"{drive} drive backslash " + ' backslash '.join(cleaned_parts)

    text = re.sub(r'\b([a-zA-Z]):\\([a-zA-Z0-9_.\\-]+)', replace_win_path, text)

    # Inline code: replace backticks and convert kebab-case and snake_case inside them
    def clean_inline_code(match):
        content = match.group(1).strip()
        # Convert kebab-case and snake_case to spaces (e.g. `infra-lab` -> `infra lab`)
        cleaned = re.sub(r'[-_]', ' ', content)
        return cleaned

    text = re.sub(r'`([^`]+)`', clean_inline_code, text)

    # Line-by-line processing for structure (headings, bullets, dividers, tables)
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line_stripped = line.strip()

        # Remove horizontal rules (---, ===, ***, ___)
        if re.match(r'^[-=*_]{3,}$', line_stripped):
            continue

        # Remove markdown table divider rows (| --- | --- |)
        if re.match(r'^\|?(\s*:?[-]+:?\s*\|)+\s*:?[-]+:?\s*\|?$', line_stripped):
            continue

        # Clean markdown table rows (| Col 1 | Col 2 |)
        if line_stripped.startswith('|') and line_stripped.endswith('|'):
            cells = [c.strip() for c in line_stripped.strip('|').split('|')]
            cleaned_lines.append(', '.join(cells) + '.')
            continue

        # Headings:
        # e.g. ## 1. Project Details -> Section 1. Project Details
        m_sec = re.match(r'^#{1,6}\s+(\d+)\.\s*(.*)$', line_stripped)
        if m_sec:
            sec_num, sec_title = m_sec.groups()
            cleaned_lines.append(f"Section {sec_num}. {sec_title}")
            continue

        m_head = re.match(r'^#{1,6}\s+(.*)$', line_stripped)
        if m_head:
            cleaned_lines.append(m_head.group(1))
            continue

        # Bullet points: *, -, +, •, ◦, ▪, ▫
        m_bullet = re.match(r'^\s*(?:[\*\-\+•◦▪▫]|\d+\.)\s+(.*)$', line)
        if m_bullet:
            content = m_bullet.group(1).strip()
            # If item doesn't end with sentence-ending punctuation, add a period
            if content and not content.endswith(('.', ':', '!', '?', ';')):
                content += '.'
            cleaned_lines.append(content)
            continue

        # Blockquotes: strip leading >
        line = re.sub(r'^\s*>\s?', '', line)

        cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)

    # Convert function calls with empty parentheses: func() -> func
    text = re.sub(r'(\b[a-zA-Z_]\w*)\(\s*\)', r'\1', text)

    # Convert function calls with arguments: func(arg) -> func of arg
    # e.g. clean_text_for_tts(text) -> clean_text_for_tts of text
    def clean_func_call(match):
        func_name = match.group(1)
        args = match.group(2).strip()
        if func_name.lower() in ('if', 'while', 'for', 'switch', 'catch', 'with'):
            return f"{func_name} {args}"
        return f"{func_name} of {args}"

    text = re.sub(r'(\b[a-zA-Z_]\w*)\(([^()]+)\)', clean_func_call, text)

    # Strip bold, italic, strikethrough markdown markers:
    # **text** or __text__
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    # *text* or _text_
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'\1', text)
    # ~~text~~
    text = re.sub(r'~~([^~]+)~~', r'\1', text)

    # Replace all remaining underscores with spaces so TTS never pronounces "underscore"
    # e.g. clean_text_for_tts -> clean text for tts, __init__ -> init
    text = re.sub(r'_+', ' ', text)

    # Remove remaining markdown punctuation characters that TTS engines read out loud
    text = re.sub(r'[*#~]', '', text)

    # Normalize multiple spaces, spaces before punctuation, and blank lines
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\s+([,.:;?!])', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()

async def get_clipboard_text():
    """Fetches text from the Windows clipboard via WSL interop."""
    try:
        # Run PowerShell command to get clipboard content
        result = subprocess.run(
            ['powershell.exe', '-Command', 'Get-Clipboard'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        raw_bytes = result.stdout
        # Attempt to decode gracefully depending on Windows system language codepages
        try:
            text = raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = raw_bytes.decode('cp850')
            except UnicodeDecodeError:
                text = raw_bytes.decode('windows-1252', errors='ignore')
                
        # Strip trailing newlines/carriage returns that powershell adds
        return text.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error reading clipboard: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("powershell.exe not found. Are you running this in WSL?", file=sys.stderr)
        return None

async def text_to_speech(text, output_file, voice, rate):
    """Converts text to speech using edge-tts and saves it."""
    
    # Format the rate string (e.g., '+20%' or '-10%')
    if rate:
        if not rate.endswith('%'):
            rate = f"{rate}%"
        if not (rate.startswith('+') or rate.startswith('-')):
            rate = f"+{rate}"
    else:
        rate = "+0%"
        
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_file)
    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        if os.path.exists(output_file):
            os.remove(output_file)
        raise RuntimeError("Generated audio file is 0 bytes. Check TTS service connection.")
    return True

def play_audio(filename):
    """Plays the audio file using mpv."""
    print(f"Playing {filename}...")
    try:
        subprocess.run(['mpv', '--no-terminal', filename], check=True)
    except subprocess.CalledProcessError:
        print(f"Error playing audio file with mpv.", file=sys.stderr)
    except FileNotFoundError:
         print("Audio player 'mpv' not found. Please 'sudo apt install mpv'.", file=sys.stderr)

async def main():
    parser = argparse.ArgumentParser(description='Convert text to high-quality audio MP3 using Edge-TTS')
    parser.add_argument('-i', '--input_file', help='Path to the input text file')
    parser.add_argument('-cl', '--clipboard', action='store_true', help='Read text from Windows clipboard')
    parser.add_argument('-o', '--output', help='Output MP3 filename (default: audio_out.mp3)')
    
    # Find list of voices by running: command-line `edge-tts --list-voices`
    parser.add_argument('-v', '--voice', default='en-US-JennyNeural', help='Voice to use (default: en-US-JennyNeural, or try en-US-GuyNeural, en-GB-SoniaNeural)')
    parser.add_argument('-r', '--rate', help='Change speed of speech (e.g. +20%% or -10%%)')
    parser.add_argument('-p', '--play', action='store_true', help='Play the audio immediately after generating')
    parser.add_argument('--no-clean', action='store_true', help='Disable markdown and text cleaning for TTS')
    
    args = parser.parse_args()
    
    text = ""
    
    if args.clipboard:
        print("Reading from Windows clipboard...")
        text = await get_clipboard_text()
        if not text:
             print("No text found in clipboard or failed to read.")
             sys.exit(1)
             
    elif args.input_file:
        if not os.path.exists(args.input_file):
            print(f"Error: Input file '{args.input_file}' not found.")
            sys.exit(1)
        with open(args.input_file, 'r', encoding='utf-8') as file:
            text = file.read().strip()
            
    else:
        print("Error: You must provide either an --input_file or use --clipboard.")
        parser.print_help()
        sys.exit(1)
        
    if not text:
        print("Error: Input text is empty.", file=sys.stderr)
        sys.exit(1)

    if not args.no_clean:
        print("Cleaning text for TTS (removing markdown, formatting paths/urls)...")
        text = clean_text_for_tts(text)
        if not text:
            print("Error: Input text is empty after cleaning.", file=sys.stderr)
            sys.exit(1)

    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        if args.input_file:
            base_name = os.path.splitext(os.path.basename(args.input_file))[0]
            output_file = f"{base_name}_audio.mp3"
        else:
             output_file = "clipboard_audio.mp3"
    
    # Ensure output has .mp3 extension
    if not output_file.endswith('.mp3'):
        output_file += '.mp3'
        
    print(f"Converting text to speech...")
    print(f"Output: {output_file}")
    print(f"Voice: {args.voice}")
    if args.rate:
        print(f"Rate: {args.rate}")
    
    try:
        await text_to_speech(text, output_file, args.voice, args.rate)
        print(f"✅ Audio saved as: {output_file}")
        
        if args.play:
            play_audio(output_file)
            
    except Exception as e:
        print(f"Error during audio generation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())