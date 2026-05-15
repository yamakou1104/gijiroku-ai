# CLAUDE.md

## Project overview
議事録AI — Meeting recording, transcription (Gemini API), and minutes generation desktop app for macOS/Windows.

## Quick start
```bash
pip install -r requirements.txt
python main.py --gui   # GUI mode
python main.py          # System tray mode
```

## Running tests
```bash
python -m pytest tests/          # All tests
python -m pytest tests/ -q       # Quiet mode
python -m pytest tests/test_X.py # Single file
```

## Architecture
- `main.py` — Entry point, component wiring, CLI flag parsing (`--gui`)
- `config.py` — Thread-safe JSON config (`~/.gijiroku-ai/config.json`) with atomic writes
- `exceptions.py` — Custom exception hierarchy (GijirokuError base, per-layer subclasses)
- `pipeline.py` — Record -> Transcribe -> Generate -> Upload pipeline with checkpoints
- `recorder/` — FFmpeg-based audio (`audio.py`) and screen+audio (`screen.py`) recording
- `transcriber/gemini.py` — Gemini API transcription with retry
- `generator/minutes.py` — Gemini API minutes generation
- `uploader/base.py` — Abstract base class for uploaders (authenticate, upload_file, create_folder, upload_session)
- `uploader/google_drive.py` — Google Drive upload with OAuth
- `uploader/onedrive.py` — OneDrive upload with MSAL OAuth
- `tray/` — System tray app (`app.py`), meeting detection (`monitor.py`), status icons (`icons.py`)
- `ui/` — Tkinter GUI (`app.py`), setup wizard (`setup.py`), custom widgets (`widgets.py`)
- `utils/` — Retry (`retry.py`), file management (`file_manager.py`), notifications (`notification.py`), encryption (`crypto.py`), resource paths (`resource_path.py`)

## Key conventions
- Python >= 3.10 required
- Platform branching via `sys.platform == "darwin"` / `"win32"`
- Secrets in `~/.gijiroku-ai/.env` (never in config.json); API key auto-migrated from config on startup
- OAuth tokens encrypted with Fernet (`utils/crypto.py`)
- Atomic file writes via `tempfile.mkstemp` + `os.replace`
- Japanese UI text, Japanese error messages
- Threading: `Lock` for shared state, `Event` for stop signals
- Factory pattern for recorder and uploader instantiation (see `_build_components` in `main.py`)
