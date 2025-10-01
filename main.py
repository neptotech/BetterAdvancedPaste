import json
from typing import List, Dict, Any
import webview
from pathlib import Path
import requests
import pyperclip
import sys
import argparse
import os

# Defaults (will be overridden by conf.json ai section if present)
AI_DEFAULTS = {
    "use_openai": False,
    "local_url": "http://127.0.0.1:8080/completion"
}

CONFIG_PATH = Path(__file__).parent / 'conf.json'

def load_ai_settings() -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Failed to parse conf.json: {e}")
    ai = data.get('ai') if isinstance(data, dict) else {}
    if not isinstance(ai, dict):
        ai = {}
    merged = {**AI_DEFAULTS, **{k: v for k, v in ai.items() if v is not None}}
    # Environment variable overrides
    # (common names: ADV_PASTE_API_KEY, OPENAI_API_KEY, ADV_PASTE_MODEL, ADV_PASTE_ENDPOINT)
    api_key_env = os.getenv('ADV_PASTE_API_KEY') or os.getenv('OPENAI_API_KEY')
    if api_key_env:
        merged['api_key'] = api_key_env
    model_env = os.getenv('ADV_PASTE_MODEL')
    if model_env:
        merged['model'] = model_env
    endpoint_env = os.getenv('ADV_PASTE_ENDPOINT')
    if endpoint_env:
        merged['endpoint'] = endpoint_env
    local_url_env = os.getenv('ADV_PASTE_LOCAL_URL')
    if local_url_env:
        merged['local_url'] = local_url_env
    use_openai_env = os.getenv('ADV_PASTE_USE_OPENAI')
    if use_openai_env is not None:
        if use_openai_env.lower() in ('0','false','no','off'):
            merged['use_openai'] = False
        elif use_openai_env.lower() in ('1','true','yes','on'):
            merged['use_openai'] = True
    return merged

AI_SETTINGS = load_ai_settings()
USE_OPENAI: bool = bool(AI_SETTINGS.get('use_openai'))
OPENAI_API_KEY: str = AI_SETTINGS.get('api_key')
OPENAI_MODEL: str = AI_SETTINGS.get('model')
OPENAI_ENDPOINT: str = AI_SETTINGS.get('endpoint')
LOCAL_URL: str = AI_SETTINGS.get('local_url')

if USE_OPENAI and not OPENAI_API_KEY:
    print("Warning: use_openai is True but no API key supplied. Set ADV_PASTE_API_KEY env var or conf.json ai.api_key.")

clipboard_text = pyperclip.paste()

def askAI(instruction):
    p1="You are a helpful AI that edits text according to user instructions."
    p2=f"""
System message:
You're clipboard assistant(meant to paste the clipboard text as per user instruction), you are supposed to convert text to output text as per instruction and give just output not your thoughts, or explanation or title, or formatting, just direct plaintext output, else you may harm the system
Edit the following text according to the instruction:

Text:
{clipboard_text}

Instruction:
{instruction}
"""
    
    # If OpenAI selected but no key, silently fallback to local if available
    effective_use_openai = USE_OPENAI and bool(OPENAI_API_KEY)
    if USE_OPENAI and not OPENAI_API_KEY:
        print("No API key present; falling back to local model endpoint.")
        effective_use_openai = False

    if effective_use_openai:
        messages = [
        {"role": "system", "content": p1},
        {"role": "user", "content": p2},
    ]
        data = {
            "model": OPENAI_MODEL,
            "messages": messages ,
            "temperature": 0,
            "max_tokens": 2048,
            "stop": ["<|user|>", "<|system|>", "</s>","<|assistant|>"]
        }
        request_url = OPENAI_ENDPOINT
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}" if OPENAI_API_KEY else "",
        "Content-Type": "application/json",}
    else:
        messages = f"""<|system|>
{p1}
<|user|>
{p2}
<|assistant|>
"""
        data = {
            "prompt": messages,
            "n_predict": -1,
            "temperature": 0,
            "top_k": 40,
            "top_p": 0.95,
            "repeat_penalty": 1.1,
            "stop": ["<|user|>", "<|system|>", "</s>","</<|assistant|>","<|assistant|>"],
        }
        request_url = LOCAL_URL
        headers = {}
    response = requests.post(request_url, json=data, headers=headers)
    x = clipboard_text
    content = ""
    if response.status_code == 200:
        rj = response.json()
        if "content" in rj:
            content = rj["content"]
            if isinstance(content, list):
                x = "".join([c.get("text","") for c in content])
            else:
                x = content
        elif "choices" in rj and rj["choices"]:
            # OpenAI style
            choice = rj["choices"][0]
            content = choice.get("text") or choice.get("message", {}).get("content", "")
            x = content
    if effective_use_openai:
        messages += [{"role": "assistant", "content": x}]
        messages += [{"role": "user", "content": "Suggest a good filename for this script (just the filename, no extra text). The name and extension should be based on the format you were asked to convert the text to, \n STRICTLY EXTENSION BASED ON INSTRUCTION(else file will be not accessible), ALSO NAME BASED ON INSTRUCTION."}]
        data2 = {
            "model": OPENAI_MODEL,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 50,
            "stop": ["<|user|>", "<|system|>", "</s>","<|assistant|>"]
        }
        request_url2 = OPENAI_ENDPOINT
        headers2 = {"Authorization": f"Bearer {OPENAI_API_KEY}" if OPENAI_API_KEY else "",
        "Content-Type": "application/json",}
    else:
        messages += f"<|assistant|>{x}\n<|user|>\nSuggest a good filename for this script (just the filename, no extra text). The name and extension should be based on the format you were asked to convert the text to, \n STRICTLY EXTENSION BASED ON INSTRUCTION(else file will be not accessible), ALSO NAME BASED ON INSTRUCTION.\n<|assistant|>\n"
        data2 = {
            "prompt": messages,
            "n_predict": 50,
            "temperature": 0,
            "stop": ["<|user|>", "<|system|>", "</s>","</<|assistant|>","<|assistant|>"],
        }
        request_url2 = LOCAL_URL
        headers2 = {}
    response2 = requests.post(request_url2, json=data2, headers=headers2)
    filename = "advanced_paste_output.txt"
    if response2.status_code == 200:
        rj2 = response2.json()
        if "content" in rj2:
            c2 = rj2["content"]
            if isinstance(c2, list):
                filename = "".join([c.get("text","") for c in c2])
            else:
                filename = c2
        elif "choices" in rj2 and rj2["choices"]:
            filename = (rj2["choices"][0].get("text") or rj2["choices"][0].get("message", {}).get("content", ""))
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
        self._settings: Dict[str, Any] | None = None
        self._window = None  # will be set after window creation

    # Internal loader
    def _load(self) -> List[Dict[str, Any]]:
        if self._cache is not None:
            return self._cache
        if not self.config_path.exists():
            print(f"Config file '{self.config_path}' not found. Using empty options list.")
            self._cache = []
            self._settings = {"save_history": True}
            return self._cache
        try:
            data = json.loads(self.config_path.read_text(encoding='utf-8'))
            # settings
            settings = data.get('settings') or {}
            if not isinstance(settings, dict):
                settings = {}
            self._settings = {
                'save_history': bool(settings.get('save_history', True))
            }
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
            if self._settings is None:
                self._settings = {"save_history": True}
        return self._cache

    # API method exposed to JS
    def get_options(self):
        return self._load()

    def get_settings(self):
        # Ensure loaded
        if self._settings is None:
            self._load()
        return self._settings or {"save_history": True}

    def set_save_history(self, value: bool):
        # Update in-memory settings and persist
        if self._settings is None:
            self._load()
        if self._settings is None:
            self._settings = {}
        self._settings['save_history'] = bool(value)
        # Persist to file without disturbing existing options
        try:
            if self.config_path.exists():
                try:
                    data = json.loads(self.config_path.read_text(encoding='utf-8'))
                except Exception:
                    data = {}
            else:
                data = {}
            data['settings'] = data.get('settings') or {}
            if not isinstance(data['settings'], dict):
                data['settings'] = {}
            data['settings']['save_history'] = self._settings['save_history']
            # Preserve options
            if 'options' not in data:
                data['options'] = []
            self.config_path.write_text(json.dumps(data, indent=2) + "\n", encoding='utf-8')
        except Exception as e:
            print(f"Failed to persist settings: {e}")
        return self._settings

    def action(self, name: str):
        print(f"Action triggered: {name}")
        try:
            content, filename_raw = askAI(name)
            filename = self._sanitize_filename(filename_raw)
            path = self.output_dir / filename
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            if self.get_settings().get('save_history', True):
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
            if self.get_settings().get('save_history', True):
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
