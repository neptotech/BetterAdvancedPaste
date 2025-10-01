import json
from typing import List, Dict, Any
import webview
from pathlib import Path
import requests
import pyperclip
import sys
import argparse

url = "http://127.0.0.1:8080/completion"

clipboard_text = pyperclip.paste()

def askAI(instruction):
    messages = f"""<|system|>
You are a helpful AI that edits text according to user instructions.
<|user|>
System message:
You're clipboard assistant(meant to paste the clipboard text as per user instruction), you are supposed to convert text to output text as per instruction and give just output not your thoughts, or explanation or title, or formatting, just direct plaintext output, else you may harm the system
Edit the following text according to the instruction:

Text:
{clipboard_text}

Instruction:
{instruction}
<|assistant|>
"""
    data = {
    "prompt": messages,
    "n_predict": -1,
    "temperature": 0,
    "top_k": 40,
    "top_p": 0.95,
    "repeat_penalty": 1.1,
    "stop": ["<|user|>", "<|system|>", "</s>","</<|assistant|>","<|assistant|>"],  # prevent infinite rambling
    }
    response = requests.post(url, json=data)
    x=clipboard_text
    if response.status_code == 200:
        # llama.cpp returns a list of chunks; join them if needed
        content = response.json()["content"]
        if isinstance(content, list):
            x=("".join([c["text"] for c in content]))
        else:
            x=content
    messages += f"<|assistant|>{content}\n<|user|>\nSuggest a good filename for this script (just the filename, no extra text). The name and extension should be based on the format you were asked to convert the text to, \n STRICTLY EXTENSION BASED ON INSTRUCTION(else file will be not accessible), ALSO NAME BASED ON INSTRUCTION.\n<|assistant|>\n"

    data2 = {
        "prompt": messages,
        "n_predict": 50,
        "temperature": 0,
        "stop": ["<|user|>", "<|system|>", "</s>","</<|assistant|>","<|assistant|>"],
    }
    response2 = requests.post(url, json=data2)
    filename="advanced_paste_output.txt"
    if response2.status_code == 200:
        content = response2.json()["content"]
        if isinstance(content, list):
            filename = "".join([c["text"] for c in content])
        else:
            filename = content
    return x, filename

"""Minimal pywebview launcher for the command palette UI.
Edit API methods to integrate real functionality.
"""

# Simple API placeholder that UI can call
class API:
    def __init__(self, config_path: Path, output_dir: Path):
        self.config_path = config_path
        self.output_dir = output_dir
        self._cache: List[Dict[str, Any]] | None = None
        self._window = None  # will be set after window creation

    # Internal loader
    def _load(self) -> List[Dict[str, Any]]:
        if self._cache is not None:
            return self._cache
        if not self.config_path.exists():
            print(f"Config file '{self.config_path}' not found. Using empty options list.")
            self._cache = []
            return self._cache
        try:
            data = json.loads(self.config_path.read_text(encoding='utf-8'))
            options = data.get('options', [])
            if not isinstance(options, list):
                raise ValueError("'options' must be a list")
            # Basic validation & normalization
            norm = []
            for o in options:
                if not isinstance(o, dict):
                    continue
                title = o.get('title')
                if not title:
                    continue
                norm.append({
                    'icon': o.get('icon', ''),
                    'color': o.get('color', '#111827'),
                    'title': title,
                    'desc': o.get('desc', '')
                })
            self._cache = norm
        except Exception as e:
            print(f"Failed to load config: {e}")
            self._cache = []
        return self._cache

    # API method exposed to JS
    def get_options(self):
        return self._load()

    def action(self, name: str):
        print(f"Action triggered: {name}")
        try:
            content, filename_raw = askAI(name)
            filename = self._sanitize_filename(filename_raw)
            path = self.output_dir / filename
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            self.save_prompt(name)
            return {"status": "ok", "file": str(path), "filename": filename}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def submit_text(self, text: str):
        print(f"User submitted text: {text}")
        try:
            content, filename_raw = askAI(text)
            filename = self._sanitize_filename(filename_raw)
            path = self.output_dir / filename
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            self.save_prompt(text)
            return {"status": "ok", "file": str(path), "filename": filename}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # Allow JS to request app shutdown after successful save
    def shutdown(self):
        try:
            import webview
            if self._window:
                webview.destroy_window(self._window)
        finally:
            # Ensure process exits even if window destroy fails
            import os
            os._exit(0)

    def _sanitize_filename(self, name: str) -> str:
        name = (name or '').strip().replace('\r','').replace('\n','')
        for ch in '<>:"/\\|?*':
            name = name.replace(ch, '_')
        if not name:
            name = 'advanced_paste_output'
        if '.' not in name:
            name += '.txt'
        return name

    def save_prompt(self, prompt: str):
        prompt = (prompt or '').strip()
        if not prompt:
            return
        try:
            if self.config_path.exists():
                try:
                    data = json.loads(self.config_path.read_text(encoding='utf-8'))
                except Exception:
                    data = {}
            else:
                data = {}
            options = data.get('options')
            if not isinstance(options, list):
                options = []
            # Avoid duplicate titles (case-insensitive)
            lower_titles = { (o.get('title') or '').strip().lower(): i for i,o in enumerate(options) if isinstance(o, dict) }
            key = prompt.lower()
            if key in lower_titles:
                # Move existing to front (recency) maybe? For now leave as-is.
                pass
            else:
                # Append new minimal entry; you can enrich later manually.
                options.append({
                    "icon": "{}",
                    "color": "#2563eb",
                    "title": prompt,
                    "desc": "Saved prompt"
                })
            data['options'] = options
            self.config_path.write_text(json.dumps(data, indent=2) + "\n", encoding='utf-8')
            # Invalidate cache so UI can show newly added prompt if reopened
            self._cache = None
        except Exception as e:
            print(f"Failed to save prompt: {e}")


def create_window(output_dir: Path):
    html_path = Path(__file__).parent / 'ui.html'
    if not html_path.exists():
        raise FileNotFoundError('ui.html not found')

    config_path = Path(__file__).parent / 'conf.json'
    api = API(config_path, output_dir)
    _ = api  # reference to avoid linter warning
    preferred_backends = ['edgechromium', 'cef', 'mshtml']
    for backend in preferred_backends:
        try:
            w = webview.create_window(
                title='Command Palette',
                url=html_path.as_uri(),
                width=420,
                height=460,
                resizable=False,
                easy_drag=True,
                frameless=False,  # Set to True for frameless palette style
                js_api=api
            )
            api._window = w
            webview.start(gui=backend, debug=False, http_server=True)
            return
        except Exception as e:
            print(f"Backend '{backend}' failed: {e}")
    # Fallback to auto
    w = webview.create_window(
        title='Command Palette',
        url=html_path.as_uri(),
        width=420,
        height=460,
        resizable=False,
        easy_drag=True,
        frameless=False,
        js_api=api
    )
    api._window = w
    webview.start(debug=False, http_server=True)


def parse_args(argv):
    parser = argparse.ArgumentParser(description='Advanced Paste AI')
    parser.add_argument('output_dir', help='Directory to save AI output file')
    return parser.parse_args(argv)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    create_window(out_dir)
