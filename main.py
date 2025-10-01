import json
from typing import List, Dict, Any
import webview
from pathlib import Path
import requests
import pyperclip

url = "http://127.0.0.1:8080/completion"

clipboard_text = pyperclip.paste()

def askAI(instruction):
    messages = f"""<|system|>
You are a helpful AI that edits text according to user instructions.
<|user|>
System message:
You're clipboard assistant, you are supposed to convert text to output text as per instruction and print just output not your thoughts, or explanation or title, or formatting, just direct plaintext output, else you may harm the system
Edit the following text according to the instruction:

Text:
{clipboard_text}

Instruction:
{instruction}
<|assistant|>
"""
    data = {
    "prompt": messages,
    "n_predict": max(512, len(clipboard_text)*1/5*2),
    "temperature": 0,
    "top_k": 40,
    "top_p": 0.95,
    "repeat_penalty": 1.1,
    "stop": ["<|user|>", "<|system|>", "</s>"],  # prevent infinite rambling
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
    messages += f"<|assistant|>{content}\n<|user|>\nSuggest a good filename for this script (just the filename, no extra text).\n<|assistant|>\n"

    data2 = {
        "prompt": messages,
        "n_predict": 50,
        "temperature": 0.5,
        "stop": ["<|user|>", "<|system|>", "</s>"],
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
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._cache: List[Dict[str, Any]] | None = None

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
        return {"status": "ok", "action": name}

    def submit_text(self, text: str):
        print(f"User submitted text: {text}")
        return {"status": "ok", "text": text}


def create_window():
    html_path = Path(__file__).parent / 'ui.html'
    if not html_path.exists():
        raise FileNotFoundError('ui.html not found')

    config_path = Path(__file__).parent / 'conf.json'
    api = API(config_path)
    _ = api  # reference to avoid linter warning
    preferred_backends = ['edgechromium', 'cef', 'mshtml']
    for backend in preferred_backends:
        try:
            webview.create_window(
                title='Command Palette',
                url=html_path.as_uri(),
                width=420,
                height=460,
                resizable=False,
                easy_drag=True,
                frameless=False,  # Set to True for frameless palette style
                js_api=api
            )
            webview.start(gui=backend, debug=False, http_server=True)
            return
        except Exception as e:
            print(f"Backend '{backend}' failed: {e}")
    # Fallback to auto
    webview.create_window(
        title='Command Palette',
        url=html_path.as_uri(),
        width=420,
        height=460,
        resizable=False,
        easy_drag=True,
        frameless=False,
        js_api=api
    )
    webview.start(debug=False, http_server=True)


if __name__ == '__main__':
    create_window()
