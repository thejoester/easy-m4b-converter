# Audiobook Converter

A lightweight Windows GUI for merging multiple audio files into a single `.m4b` audiobook with chapter markers — powered by ffmpeg under the hood.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Platform](https://img.shields.io/badge/platform-Windows-lightgrey) ![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- Drag and drop audio files or folders onto the window
- Auto-detects output filename from file metadata (album/title tags) or common filename prefix
- Auto-detects source bitrate and defaults to it — never re-encodes higher than the source
- Previews file order before processing so you can catch bad naming before it starts
- Embeds chapter markers from each source file (chapter titles taken from filenames)
- Sets the `album` metadata tag on the output to match the filename
- Per-file progress bar and conversion log
- Shows elapsed time on completion
- No console window popup

## Supported Input Formats

`.mp3` `.m4a` `.aac` `.flac` `.wav` `.ogg`

---

## Requirements

### Running from source

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) installed and available on your PATH
- Python dependencies:

```
pip install tkinterdnd2 pillow
```

> **Note:** `tkinterdnd2` is required for drag-and-drop support. Without it the app will still launch but you won't be able to drop files.

### Installing ffmpeg on Windows

```
winget install ffmpeg
```

Or download manually from [ffmpeg.org](https://ffmpeg.org/download.html) and add the `bin` folder to your system PATH.

---

## Usage

### From source

```
python audiobook-converter.pyw
```

### From the pre-built EXE

Download the latest release from the [Releases](../../releases) page and run `AudiobookConverter-vX.X.X.exe` — no installation needed.

---

## How It Works

1. **Drop** your audio files (or a folder) onto the window
2. The app reads metadata and auto-fills the output filename and bitrate
3. **Review** the file order in the log — files are sorted by filename
4. Hit **▶ Start Conversion** if the order looks correct, or ❌ to cancel and re-drop
5. Each file is encoded to AAC individually (progress shown per file), then merged into a single `.m4b` with chapter markers injected
6. The output file is saved to the same folder as your source files

---

## Building the EXE

The included `build.yml` GitHub Actions workflow builds a standalone Windows EXE automatically when you push a tag:

```
git tag v1.0.0
git push origin v1.0.0
```

The release will appear under [Releases](../../releases) with the EXE attached.

To build locally:

```
pip install pyinstaller tkinterdnd2 pillow
pyinstaller --noconfirm --onefile --windowed --icon=audiobook-converter.ico --collect-all tkinterdnd2 audiobook-converter.pyw
```

Output will be in the `dist/` folder.

---

## Why not just use AudioBookConverter?

AudioBookConverter is great but can lock up the CPU on large batches. This tool delegates all the heavy lifting directly to ffmpeg, keeping the GUI responsive and CPU usage predictable.

---

## License

MIT