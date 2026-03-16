# Audiobook Converter

A lightweight Windows app for merging multiple audio files into a single `.m4b` audiobook with chapter markers.

![Platform](https://img.shields.io/badge/platform-Windows-lightgrey) ![License](https://img.shields.io/badge/license-MIT-green)

---

## Download

Grab the latest `AudiobookConverter-vX.X.X.exe` from the [Releases](../../releases) page — no installation required.

---

## Requirements

[ffmpeg](https://ffmpeg.org/download.html) must be installed and available on your PATH.

**Quick install via winget:**
```
winget install ffmpeg
```

---

## Usage

1. **Drop** your audio files (or a folder) onto the window
2. The app auto-fills the output filename and bitrate from your file metadata
3. **Review** the file order in the log — files are sorted by filename
4. Hit **▶ Start Conversion** if the order looks correct, or ❌ to cancel and re-drop
5. The finished `.m4b` is saved to the same folder as your source files

---

## Features

- Supports `.mp3` `.m4a` `.aac` `.flac` `.wav` `.ogg`
- Auto-detects output filename from metadata tags or common filename prefix
- Auto-detects source bitrate — never re-encodes higher than the source
- Embeds chapter markers, one per source file
- Sets the `album` tag on the output to match the filename
- Per-file progress bar and conversion log
- Shows elapsed time on completion

---

<details>
<summary>Building from source</summary>

### Requirements

- Python 3.10+
- ffmpeg on PATH
- Dependencies: `pip install tkinterdnd2 pillow`

### Run

```
python audiobook-converter.pyw
```

### Build EXE locally

```
pip install pyinstaller tkinterdnd2 pillow
pyinstaller --noconfirm --onefile --windowed --icon=audiobook-converter.ico --collect-all tkinterdnd2 audiobook-converter.pyw
```

### Build and release via GitHub Actions

Push a tag and the workflow handles the rest:

```
git tag v1.0.0
git push origin v1.0.0
```

</details>

---

## License

MIT
