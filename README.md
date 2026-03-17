# Easy M4B Converter

A lightweight Windows app for merging multiple audio files into a single `.m4b` audiobook with editable output metadata and chapter markers.

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
2. The app auto-detects metadata from your first file (album artist, album, series, part) and source bitrate
3. Review and edit metadata fields, bitrate, and output filename before converting
4. **Review** the file order in the log — files are sorted by filename
5. Hit **▶ Start Conversion** if the order looks correct, or ❌ to cancel and re-drop
6. The finished `.m4b` is saved to the same folder as your source files, using the filename you set

---

## Features

- Supports `.mp3` `.m4a` `.aac` `.flac` `.wav` `.ogg`
- Auto-detects album artist, album, series, part, and source bitrate from input metadata
- Auto-builds output filename from detected metadata, with manual filename editing support
- Lets you edit output metadata fields before conversion
- Auto-detects source bitrate — never re-encodes higher than the source
- Embeds chapter markers, one per source file
- Writes output tags for album, artist/album artist, series/show/grouping, and part when provided
- Detects chapter count in the new output and warns in the log if only `1` or `0` chapters are found
- Per-file progress bar and conversion log
- Shows elapsed time on completion

---

## M4B Chapter Editor

*M4B chapter editor* is a companion tool for editing chapter structure in a single `.m4b` file.

### What it does

- Accepts one dropped `.m4b` file (folders are not supported)
- Detects existing chapter count
- Splits chapters at fixed intervals (`01` to `60` minutes)
- Writes a **new** output `.m4b` with updated chapters

### Usage

1. Run `m4b-chapter-editor.pyw`
2. Drag and drop one `.m4b` file onto the window
3. Confirm detected chapter count
4. Set `Set chapters every` value (`01` to `60`)
5. If duration is unknown, enter manual duration as **hours** and **minutes**
6. Click `Set Chapters`

### Notes

- Existing chapters are overwritten in the **new output file**
- The original source file is not modified
- Output is saved next to the source with a `- chapters-XXm` suffix
- ffmpeg stream mapping keeps audio (and optional cover art) while skipping incompatible subtitle/data streams

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
python m4b-chapter-editor.pyw
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
