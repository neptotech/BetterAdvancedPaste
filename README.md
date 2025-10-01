# PyWebView Command Palette UI

A minimal replica of the Windows clipboard / AI assist style command palette using **pywebview**. Functionality hooks are placeholders; focus is on UI structure so you can wire your own logic.

## Features
- PyWebView desktop window (Edge / Chromium backend if available)
- Search bar header with accent icon
- Scrollable action list, keyboard navigation (↑ ↓ Enter)
- Dynamic options loaded from `conf.json` (no code changes needed to add items)
- Simple Python API: `get_options`, `action`, `submit_text`
- Press Enter with text in the search box to send that text to Python (`submit_text`)

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
python main.py
```
If Edge backend fails you can remove `gui='edgechromium'` logic in `main.py` to fall back to default.

## Configuration: `conf.json`
Options are defined externally so you can add new commands without editing code.

Example:
```json
{
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

## Extending Behavior
- Handle option selection: update `API.action` in `main.py` to perform real logic based on `name`.
- Handle free-form text: modify `API.submit_text` to route the user-entered text to an AI model / backend.
- Add more API methods: define them on the `API` class; in JS call `window.pywebview.api.methodName(args...)`.
- Make window frameless: set `frameless=True` in `create_window()` and add custom window controls.

## Notes
- Image-related demo actions have been removed; only text-focused paste options remain.
- No persistence or system clipboard integration included—add via additional Python libraries if needed.
- For production, consider validation, logging, and error UI for API failures.
