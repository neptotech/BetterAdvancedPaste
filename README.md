# AI Clipboard Transformer Palette

A minimal **pywebview** command palette that captures your clipboard, lets you type an instruction (or pick a preset), sends both to a local AI endpoint (llama.cpp style), then saves the transformed text to a file with an AI‑suggested filename in a target folder you provide on startup.

## Features
- Clipboard captured at launch (plain text) using `pyperclip`
- Type an instruction OR pick a predefined option (its title becomes the instruction)
- Sends clipboard + instruction to local AI endpoint (`http://127.0.0.1:8080/completion`)
- Second AI call suggests a good filename (sanitized + `.txt` added if missing)
- Saves result into the output directory you pass as the first CLI argument
- PyWebView desktop window (Edge / Chromium backend preferred)
- Keyboard navigation (↑ ↓ Enter)
- Options loaded from `conf.json`
- API methods: `get_options`, `action`, `submit_text` (both run the AI pipeline)

## Keyboard & Interaction
| Key / Action | Behavior |
|--------------|----------|
| ↑ / ↓        | Move selection among filtered options |
| Typing       | Filters options by title/description |
| Enter (text present) | Submits the typed text to Python (`submit_text`) |
| Enter (empty box) | Triggers the currently highlighted option (`action`) |

## Project Layout
```
main.py          # Starts the pywebview window & exposes API
ui.html          # HTML/CSS/JS for the palette UI logic
conf.json        # Configuration-driven option list
requirements.txt # Python dependency pin
README.md        # This file
```

## Install & Run
Create a virtual environment (recommended) then install dependencies.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py D:\\Files\\   # <- choose your output directory
```
If Edge backend fails the app will attempt other backends then fallback to auto.

The first argument is required: it is where generated files will be saved. It will be created if it does not exist.

### Local AI Endpoint
This project expects a llama.cpp compatible HTTP server at `http://127.0.0.1:8080/completion` returning JSON chunks like:
```json
{
	"content": [ {"text": "..."}, {"text": "..."} ]
}
```
Adjust `AI_URL` in `main.py` if your endpoint differs.

## Configuration: `conf.json`
Options are defined externally so you can add new commands without editing code. A new `ai` section controls whether an OpenAI‑compatible endpoint is used or a local llama.cpp style server.

Example (abridged):
```json
{
	"ai": {
		"use_openai": true,
		"api_key": "YOUR_API_KEY_HERE",
		"model": "gpt-3.5-turbo",
		"endpoint": "https://api.chatanywhere.tech/v1/chat/completions",
		"local_url": "http://127.0.0.1:8080/completion"
	},
	"options": [
		{ "icon": "AA", "color": "#2563eb", "title": "Paste as plain text", "desc": "Strip formatting and paste" },
		{ "icon": "{}", "color": "#7e22ce", "title": "Paste as markdown", "desc": "Format content as Markdown" }
	]
}
```
Fields:
- `icon` (string) short label shown in colored square
- `color` (hex) background for the icon square
- `title` (string, required) command name
- `desc` (string) secondary description / hint

On load, the frontend calls `get_options()`; invalid or missing fields are skipped. If `conf.json` is absent, an empty list (fallback sample in dev) is used.

### AI Section Fields
| Field | Type | Description |
|-------|------|-------------|
| `use_openai` | bool | If true, uses an OpenAI chat completion style request. If false (or missing / no key), falls back to local URL. |
| `api_key` | string | API key for remote endpoint. If blank and `use_openai=true`, a warning is printed and local fallback is attempted. |
| `model` | string | Model name passed to the OpenAI‑compatible API. |
| `endpoint` | string | Chat completion endpoint (POST). |
| `local_url` | string | Local llama.cpp style endpoint used when not using OpenAI or when key missing. |

### Environment Variable Overrides
You can override values without editing the file:

| Env Var | Overrides |
|---------|----------|
| `ADV_PASTE_API_KEY` / `OPENAI_API_KEY` | ai.api_key |
| `ADV_PASTE_MODEL` | ai.model |
| `ADV_PASTE_ENDPOINT` | ai.endpoint |
| `ADV_PASTE_LOCAL_URL` | ai.local_url |
| `ADV_PASTE_USE_OPENAI` | ai.use_openai (values: 1/0, true/false, yes/no) |

If `use_openai` is true but no key is provided (file and env both empty) the app prints a warning and automatically uses the local endpoint instead.

## Extending Behavior
- Change model params (temperature, n_predict) inside `call_local_ai` or when invoking it.
- Use a different save format (e.g., add extension inference) in `_process_instruction` of the `API` class.
- Add metadata sidecar (e.g., JSON with prompt + timestamp) after writing the main file.
- Make window frameless: set `frameless=True` in `create_window()` and add custom controls.
- Add streaming: adapt `call_local_ai` to handle server-sent events or partial chunks.

## Notes
- Filename is sanitized (invalid Windows characters replaced with `_`). `.txt` enforced if missing.
- If AI filename generation fails, a timestamped fallback is used (e.g., `output_YYYYmmdd_HHMMSS.txt`).
- Errors from the AI call are surfaced back to the JS console (see DevTools) via returned status.
- Clipboard is read only once at startup; re-run app if you want to process a changed clipboard (or extend to recapture on each instruction).
- Minimal error UI—extend JS to show toast/snackbar for better UX.
