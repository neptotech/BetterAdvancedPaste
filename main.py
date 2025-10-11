import json
from typing import List, Dict, Any
import webview
from pathlib import Path
import requests
import pyperclip
import sys
import argparse
import getpass
import keyring
import os
# Defaults (will be overridden by conf.json ai section if present)
AI_DEFAULTS = {
    "use_openai": False,
    "local_url": "http://127.0.0.1:8080/completion"
}

def _resource_path(name: str) -> Path:
    """Return absolute path to a bundled resource (handles PyInstaller/Nuitka)."""
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    return base / name


def _app_config_dir() -> Path:
    """Return per-user writable config directory."""
    if sys.platform.startswith('win'):
        base = os.environ.get('APPDATA') or str(Path.home() / 'AppData' / 'Roaming')
        return Path(base) / 'BetterAdvancedPaste'
    elif sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'BetterAdvancedPaste'
    else:
        return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'BetterAdvancedPaste'


def _exe_dir() -> Path:
    """Directory of the running executable (or script during dev)."""
    if getattr(sys, 'frozen', False):
        # PyInstaller/Nuitka onefile
        try:
            return Path(sys.executable).resolve().parent
        except Exception:
            pass
    return Path(__file__).resolve().parent


def _resolve_config_path() -> Path:
    """Choose config location with this precedence:
    1) BAP_CONFIG env var (file path)
    2) conf.json next to the EXE (portable mode) if present
    3) %APPDATA%/BetterAdvancedPaste/conf.json (or OS equivalent)
    """
    env_path = os.environ.get('BAP_CONFIG')
    if env_path:
        return Path(env_path).expanduser().resolve()
    portable = _exe_dir() / 'conf.json'
    if portable.exists():
        return portable
    return _app_config_dir() / 'conf.json'


CONFIG_PATH = _resolve_config_path()

# Keyring identifiers
SERVICE_NAME = "BetterAdvancedPaste"
USERNAME = getpass.getuser()

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
    return merged

AI_SETTINGS = load_ai_settings()
USE_OPENAI: bool = bool(AI_SETTINGS.get('use_openai'))
OPENAI_API_KEY: str = AI_SETTINGS.get('api_key')
OPENAI_MODEL: str = AI_SETTINGS.get('model')
OPENAI_ENDPOINT: str = AI_SETTINGS.get('endpoint')
LOCAL_URL: str = AI_SETTINGS.get('local_url')


clipboard_text = pyperclip.paste()


def _get_keyring_token() -> str | None:
    try:
        return keyring.get_password(SERVICE_NAME, USERNAME)
    except Exception:
        return None


def _set_keyring_token(value: str | None) -> None:
    try:
        if value:
            keyring.set_password(SERVICE_NAME, USERNAME, value)
        else:
            # empty/None deletes
            try:
                keyring.delete_password(SERVICE_NAME, USERNAME)
            except Exception:
                pass
    except Exception as e:
        raise e

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
    
    # Resolve API key: prefer keyring token if set, else config/env
    openai_key_effective = _get_keyring_token() or OPENAI_API_KEY
    # If OpenAI selected but no key, silently fallback to local if available
    effective_use_openai = USE_OPENAI and bool(openai_key_effective)
    if USE_OPENAI and not openai_key_effective:
        print("No API key present; falling back to local model endpoint.")
        effective_use_openai = False

    if effective_use_openai:
        messages_chat = [
            {"role": "system", "content": p1},
            {"role": "user", "content": p2},
        ]
        data = {
            "model": OPENAI_MODEL,
            "messages": messages_chat,
            "temperature": 0,
            "max_tokens": 2048,
            "stop": ["<|user|>", "<|system|>", "</s>","<|assistant|>"]
        }
        request_url = OPENAI_ENDPOINT
        headers = {"Authorization": f"Bearer {openai_key_effective}" if openai_key_effective else "",
                   "Content-Type": "application/json",}
    else:
        prompt = f"""<|system|>
{p1}
<|user|>
{p2}
<|assistant|>
"""
        data = {
            "prompt": prompt,
            "n_predict": -1,
            "temperature": 0,
            "top_k": 40,
            "top_p": 0.95,
            "repeat_penalty": 1.1,
            "stop": ["<|user|>", "<|system|>", "</s>","</<|assistant|>","<|assistant|>"],
        }
        request_url = LOCAL_URL
        headers = {}

    # Primary completion request: must succeed or we fail the action
    try:
        response = requests.post(request_url, json=data, headers=headers)
        response.raise_for_status()
    except Exception as e:
        # Make OpenAI auth/malformed key errors bubble up to stop shutdown
        raise RuntimeError(f"AI request failed: {e}")

    x = ""
    try:
        rj = response.json()
    except Exception:
        raise RuntimeError("AI response was not JSON")

    if "content" in rj:
        content = rj["content"]
        if isinstance(content, list):
            x = "".join([c.get("text","") for c in content])
        else:
            x = str(content)
    elif "choices" in rj and rj["choices"]:
        # OpenAI style
        choice = rj["choices"][0]
        x = choice.get("text") or choice.get("message", {}).get("content", "")
    else:
        raise RuntimeError("AI response missing expected fields")

    if not (x or "").strip():
        raise RuntimeError("AI returned empty result")
    # Secondary filename suggestion: best-effort; failures fall back to default
    filename = "advanced_paste_output.txt"
    try:
        if effective_use_openai:
            messages_chat += [{"role": "assistant", "content": x}]
            messages_chat += [{"role": "user", "content": "Suggest a good filename for this script (just the filename, no extra text). The name and extension should be based on the format you were asked to convert the text to, \n STRICTLY EXTENSION BASED ON INSTRUCTION(else file will be not accessible), ALSO NAME BASED ON INSTRUCTION."}]
            data2 = {
                "model": OPENAI_MODEL,
                "messages": messages_chat,
                "temperature": 0,
                "max_tokens": 50,
                "stop": ["<|user|>", "<|system|>", "</s>","<|assistant|>"]
            }
            request_url2 = OPENAI_ENDPOINT
            headers2 = {"Authorization": f"Bearer {openai_key_effective}" if openai_key_effective else "",
                        "Content-Type": "application/json",}
        else:
            prompt2 = f"<|assistant|>{x}\n<|user|>\nSuggest a good filename for this script (just the filename, no extra text). The name and extension should be based on the format you were asked to convert the text to, \n STRICTLY EXTENSION BASED ON INSTRUCTION(else file will be not accessible), ALSO NAME BASED ON INSTRUCTION.\n<|assistant|>\n"
            data2 = {
                "prompt": prompt2,
                "n_predict": 50,
                "temperature": 0,
                "stop": ["<|user|>", "<|system|>", "</s>","</<|assistant|>","<|assistant|>"],
            }
            request_url2 = LOCAL_URL
            headers2 = {}
        response2 = requests.post(request_url2, json=data2, headers=headers2)
        if response2.status_code == 200:
            rj2 = response2.json()
            if "content" in rj2:
                c2 = rj2["content"]
                if isinstance(c2, list):
                    filename = "".join([c.get("text","") for c in c2])
                else:
                    filename = str(c2)
            elif "choices" in rj2 and rj2["choices"]:
                filename = (rj2["choices"][0].get("text") or rj2["choices"][0].get("message", {}).get("content", ""))
    except Exception:
        # keep default filename on any error
        pass
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
        self._settings_window = None  # secondary popup window
        self._settings_creating = False  # debounce flag
        self._settings_closing = False   # prevent duplicate closes

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

    # --- Keyring-backed API token methods ---
    def get_api_token(self) -> str:
        """Return current API token from keyring (or empty string if none)."""
        tok = _get_keyring_token()
        return tok or ""

    def set_api_token(self, token: str) -> bool:
        """Set/replace API token in keyring. Empty string clears it."""
        try:
            _set_keyring_token(token.strip() or None)
            return True
        except Exception as e:
            print(f"Failed to set API token: {e}")
            return False

    def open_settings(self):
        """Show the settings popup window, creating it on demand if necessary."""
        try:
            if self._settings_creating:
                print("[settings] open ignored (already creating)")
                return True
            if self._settings_window is None:
                settings_html = _resource_path('settings.html')
                if not settings_html.exists():
                    print("[settings] settings.html missing")
                    return False
                # Resolve window icon if available
                _icon = _resource_path('icon.ico')
                _icon_arg = str(_icon) if _icon.exists() else None
                self._settings_creating = True
                try:
                    print("[settings] creating window")
                    try:
                        w = webview.create_window(
                            title='Settings',
                            url=settings_html.as_uri(),
                            width=500,
                            height=250,
                            resizable=False,
                            on_top=True,
                            js_api=self,
                            icon=_icon_arg
                        )
                    except TypeError:
                        w = webview.create_window(
                            title='Settings',
                            url=settings_html.as_uri(),
                            width=500,
                            height=250,
                            resizable=False,
                            on_top=True,
                            js_api=self
                        )
                    # Attach close event if available
                    try:
                        if hasattr(w, 'events') and hasattr(w.events, 'closed'):
                            w.events.closed += lambda: self._on_settings_closed()
                    except Exception:
                        pass
                    self._settings_window = w
                    return True
                finally:
                    self._settings_creating = False
            else:
                try:
                    print("[settings] showing existing window")
                    self._settings_window.show()
                    self._settings_window.bring_to_front()
                    return True
                except Exception:
                    print("[settings] existing reference invalid, recreating")
                    self._settings_window = None
                    return self.open_settings()
        except Exception as e:
            print(f"Failed to open settings window: {e}")
            return False

    def _on_settings_closed(self):
        print("[settings] window closed event")
        self._settings_window = None

    def close_settings(self) -> bool:
        """Destroy the settings window to avoid backend inconsistencies across GUIs."""
        try:
            if self._settings_closing:
                print("[settings] close ignored (already closing)")
                return True
            self._settings_closing = True
            if self._settings_window:
                try:
                    print("[settings] destroy window")
                    if hasattr(self._settings_window, 'destroy'):
                        self._settings_window.destroy()
                    else:
                        print("[settings] no destroy(); hiding instead")
                        self._settings_window.hide()
                except Exception as e:
                    print(f"[settings] destroy/hide failed: {e}")
                finally:
                    self._settings_window = None
                    self._settings_closing = False
                return True
            # no window present
            self._settings_closing = False
            return False
        except Exception as e:
            print(f"Failed to close settings window: {e}")
            return False

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
            # Destroy settings window first if present
            try:
                if self._settings_window:
                    print("[shutdown] destroying settings window")
                    try:
                        if hasattr(self._settings_window, 'destroy'):
                            self._settings_window.destroy()
                        else:
                            self._settings_window.hide()
                    except Exception as e:
                        print(f"[shutdown] settings destroy/hide failed: {e}")
                    self._settings_window = None
            except Exception:
                pass
            # Then destroy main window
            if self._window:
                print("[shutdown] destroying main window")
                try:
                    if hasattr(self._window, 'destroy'):
                        self._window.destroy()
                    else:
                        self._window.hide()
                except Exception as e:
                    print(f"[shutdown] main destroy/hide failed: {e}")
                self._window = None
        finally:
            # Ensure process exits even if window destroy fails
            import os
            print("[shutdown] exiting process")
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
    html_path = _resource_path('ui.html')
    if not html_path.exists():
        raise FileNotFoundError('ui.html not found')

    # Ensure config directory exists for read/write
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    config_path = CONFIG_PATH
    api = API(config_path, output_dir)
    _ = api  # reference to avoid linter warning
    preferred_backends = ['edgechromium', 'cef', 'mshtml']
    # Resolve window icon if present
    icon_path = _resource_path('icon.ico')
    icon_arg = str(icon_path) if icon_path.exists() else None
    for backend in preferred_backends:
        try:
            try:
                w = webview.create_window(
                    title='Command Palette',
                    url=html_path.as_uri(),
                    width=420,
                    height=460,
                    resizable=False,
                    easy_drag=True,
                    frameless=False,  # Set to True for frameless palette style
                    js_api=api,
                    icon=icon_arg
                )
            except TypeError:
                # Older pywebview without 'icon' kw support
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
            def _on_start():
                # Nothing to do at start; windows already created
                pass
            webview.start(_on_start, gui=backend, debug=False, http_server=True)
            return
        except Exception as e:
            print(f"Backend '{backend}' failed: {e}")
    # Fallback to auto
    try:
        w = webview.create_window(
            title='Command Palette',
            url=html_path.as_uri(),
            width=420,
            height=460,
            resizable=False,
            easy_drag=True,
            frameless=False,
            js_api=api,
            icon=icon_arg
        )
    except TypeError:
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
    def _on_start2():
        # Nothing to do at start
        pass
    webview.start(_on_start2, debug=False, http_server=True)


def parse_args(argv):
    parser = argparse.ArgumentParser(description='Advanced Paste AI')
    parser.add_argument('output_dir', help='Directory to save AI output file')
    return parser.parse_args(argv)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    create_window(out_dir)
