# Fero Rhythm Bank

This project provides a small desktop utility for managing Yamaha-style rhythm banks,
editing section metadata, and playing back WAV files with real-time tempo control.

## Project Structure

```
app/
├── __init__.py          # Package initialization and rhythm directory bootstrap
├── models.py            # Dataclasses describing rhythms, sections, and time signatures
├── player.py            # Audio playback engine with time-stretching and crossfade support
├── rhythm_bank.py       # Persistence layer for storing rhythms on disk
└── ui/
    ├── __init__.py
    ├── main_window.py   # Tkinter application that wires the UI to the backend
    └── rhythm_editor.py # Dialog for editing tempo, time signature, and section WAV files
rhythms/                 # Automatically created directory containing saved rhythms
```

## Getting Started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install librosa sounddevice numpy
   ```

   Tkinter ships with the default CPython distribution on most platforms. If you are
   using a minimal distribution (for example some Linux Docker images), install the
   system Tk bindings via your package manager (e.g. `apt-get install python3-tk`).

2. **Run the application**

   ```bash
   python -m app.ui.main_window
   ```

   The first launch automatically creates the `rhythms/` directory in the project root.

## Features

* **Rhythm Bank** – Lists all saved rhythms, showing their tempo and time signature.
* **Rhythm Editor** – Lets you assign WAV files to sections (Intro A/B, Main A–D,
  Fill A–D, Ending, Break, etc.), update tempo and time signature, and persist your
  changes. Uploaded WAV files are copied into `rhythms/<name>/` alongside a JSON
  metadata file.
* **Playback Engine** – Loads section WAV files with `librosa`, performs real-time
  time-stretching while preserving pitch, and plays audio via `sounddevice`. Section
  changes crossfade smoothly and Yamaha-style fill logic automatically triggers the
  matching fill when you switch between main variations.
* **Tempo Control** – Adjust the tempo slider to time-stretch all sections while
  playback continues.

## Notes on Audio Playback

* The player requires `librosa` for decoding and time-stretching along with the
  `sounddevice` package (PortAudio bindings) for audio output. On some platforms you
  may need to install PortAudio separately.
* When changing the tempo significantly, the rendered audio must be re-generated.
  The UI performs this automatically, but very long files can take a moment to process.

## Development Tips

* Rhythms are stored as JSON metadata under `rhythms/<rhythm_name>/metadata.json` with
  their section WAV files in the same directory. You can back up or share rhythms by
  copying these folders.
* The `RhythmBank` class exposes simple CRUD helpers (`list_rhythms`, `load`, `save`,
  `delete`) that can be reused by alternative interfaces if you need to integrate with
  other tools.
* The `Player` class can be used independently of the UI if you want to build command
  line tooling or automated playback.
