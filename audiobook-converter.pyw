import os
import sys
import re
import time
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

SUPPORTED_FORMATS = (".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg")

try:
    import tkinterdnd2 as tkdnd
    root = tkdnd.TkinterDnD.Tk()
    dnd_available = True
except ImportError:
    root = tk.Tk()
    dnd_available = False

root.title("Easy M4B Converter")
root.geometry("800x600")
root.minsize(380, 500)
root.resizable(True, True)

_ICON_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAARv0lEQVR4nJ2aebTdVXXHP+f8"
    "fr87vunde9zK8JC8QwhwCgQi6QMSiDI0MClhFUIGKCl210uWiK0vtqugCWV2liktrK2JBq2J"
    "bFCccEDASBjEtJASSkBDy8pK8ebjjbzpn94/fnV4SIPTcdYffcO/7fs/Ze5+9v/spByXCkQ/"
    "1pu84/K9L487mVfW6d7/2cN/sF+aP5M8qBSLJe4JCHXJPC9q8Q5l3+MaTc+hwjwTi/FlS"
    "8y6qxrFuoVdtIof8hiANpEo1z5Cw/3+ONyQwH3ITXAfY1qNxXs3/VvtOaaxSE6wgjRUQBFrP"
    "Q83r8EOOnEALhjoYtGrYjWqc1w0qijaBNmCUINjGkW3MvLR+V8QmP3dEK6LemMC8OVQJvBYB"
    "pTtAOygctHbQSqOURolqwBd009bFYsVgJcZiGk9L4gvNO1vGdgSr8DoE2uAVSjXnVTdmXDeA"
    "e2jt4WgPBw8TeQTiYehBu124ykGbAGwdhY+iikeI41qsxEQSEhMlRJRtGJVglW05efv1NXBq"
    "1CHXO+25ZSzKQVBoNBoXpdK4bgYtaWqmgO0+nkXHreb4NSdzzHFDDC7opeikyNUM8XSV8v5Z"
    "Dmzfzavv/A8wx9YxaqKQENqGREisGqsighVBGkSktS4HDzmUQBN8074T83QaZuHg4KHdLK7O"
    "UjcLYPk5nPvedVx8yVs46rgewhCmRqAyAjJm6arFLEx5LO9TLM5DRmB0zzgbf7uBx//wM16M"
    "/0jdKRNKSCA+MTExBtNaD0FEXpPEPAKdNq+URnWai3LRKo3r5lGSo9yzlnOuuY5P/NX5uH2K"
    "3z9r2PjrnYw9+xLhyC505QBuWCZtY/KSpqj7WJFbxpnLTuYda09h1VkD1KzPw//xcx74wz1s"
    "Zxt1J6Bqa4RExNjGI3F82+HY8toEOsCjkqvKScA7WVynG2sLyOrLuPX2T3LWOQPc91CFX92/"
    "gWDLBtKzW3HMfpRUQGJEIhQWRzSOKFzxyNlelslK3tlzPled/25OvPpYRrYMc88/38Evqr9h"
    "xq1RtjUCImJJVsKKtJxdXotAYipNV03Ao1y0m0GyA2jdhWN6yb/7Ou766keYjuH2Lz3D1M+/"
    "R1fpWYRZRCLExoiJAJOEULFoNA4KF42LgwOkSbPKrOKGxVdyyS2XIkvTfHf9l7hv73+y360w"
    "Z2vUiYnFECNY6STQNqcOAh1OqxzAwfXSBFGaq770NWLj8diuOt/9xtX87vmAu2/9Hl3PfR9l"
    "92NsgJgQpQStwMYxIjFCDCI4OHhK46qEirYKV2kcpVgoBT7mXsQ1N3+EzLuGePBvbuObux5k"
    "2K0za+v40opTLV+wHQRaYbS5wzYDplIapV1stp+jVhxN4Zwzebvx+emTs9z7uXvpfelHRHYa"
    "G9dREgEOgkfZj+nyMmhCrBUUFheFh4MTA8R4joeRCEExyTTfMj/B+cYYH87cxBV3fQr/Y3v5"
    "9uRTGB0nO4VYBIUh2cmTPSYhoZtbU9uu2huVUi7kehjzDdcsNSzvcRkq9HLGUDeVaBYxdURi"
    "QKNU07tWfO7WO/n4X53P3adgx87tWPjb75L7/kEXS5HW2fI4OGSlPXJi2q7YGoFkIIea5eOP"
    "hYJPbKS/cQMuU7gfElkNMHc4f6cGz+H3d0bBvuvYQr+V3nHVhBz7YxGxJLRtOOaAdVQfb2T"
    "6xY2kGJnTZUHBqhgbLzKE5Q6yCJYa2A1JfO3xGmI0mXOUF3TmU6/L7t1TnJD5KSn8E76MAi"
    "ixJBpIcBKCXC2kBjH5T82YsLKF2YkFIxj9p3y6N6c4hFj3OB96OReTJAe1UNbJQ4kegcDL6G"
    "m5b6y8DUKq0KWMjMYWA5VaKPJAtlRPR5d4nPeSBBFSKYJpH+EpC3KMoQHPw5dHQOg3sB4BRx"
    "i0wHqS2qqnakFgvJaSMQHyWsBj1RmgO7qmQZZGQOqU2j5XiEKl/aQvBPsV6Mn5RvVCIZWBpS"
    "rRBXO0SSnBTlrJKY4D4XJgwX6b5TBGrHiNbVMGsCqCk1NMjDBJ6UlP4AKpqGE4V+IH9yInFM"
    "lZ0YqQYxhxJ7VMEkp8nJV4I3GCuMGcMt5cFyS7dITtNQPxl4Cte3CrWqQeP8S/VDqUPgNgii"
    "xPJBfJWxKKZnYeWDGGEg8SFz73s0bgICmDg2rDomkHtIb0dILaRqKVfXk1jMqvMDVkA+uijY"
    "BZlYEaFiH1c2iu+mVfpGjAYrHlY0mJXtqfaGFCeGCkJVhXQQiOYGmLTKzV6e7xzolNJ3EBN3"
    "EMHjWcxQTSmLWU7h1LDqbVmipqd11oYXmtJlCLr48h8FWu2aAVJfWE0ZMicHBKf/ZoiBZfgp"
    "x9B8Sln2KQ34I79BFrh3RrjMxaFqHJuJRMbvBzaV5wuUBLx3e0fH0Dj2nnEqNnGJWcNFZuQk"
    "Y6pjYLxakzHVcKKcYCGGtjhDJGaRDaIYMVRo2m7gmvCoRFcgfumzxkVnxSwOoWRQNmvONEpK"
    "mBXDkALUMPcaWTJFIJbmXf93C4J3DaBfx+Bm1MlBJILelLUG4oR4OTSMiUhJxFnLI3u4nM5U"
    "xJRWuWXJQ6tN03JDYD7x8mRKIjWLDcHHZKW7toCiZHBzN1nAOimUONvtNJZHJRsJ6x3YEPD0"
    "pAoMkRSMCpqXPiLo4E10fRBGqVH9lq1fNbzSwBQ6F0lB65bIHdS5mhoCkYLBkx5VEjr5blLF"
    "E+rNDCT1N2I1d7v6ZvCDHWH0HjMHJHixEV/I7iAFbsOqGmhGn5qJoEd7VmF8N4LdJJGvmpEF"
    "k7XWiTPAa60v9e9B1W3I5L7BrtNoHjHZJhcQD5jn8pLKT5q6wMWUNrWLfqN4ywEVqoCXSqOF"
    "VZHIjBixL9pA4jZkPgTcISa1C84jL7q+lkYbCcRCpqgb3Fbl4iy6NjQ3VGUqiOB1/a6i3nHf"
    "aNBwHBHxoYULdC3y1i7EVvKvDAqiKBe3Cln9hI3LxOtaVFvW5FBBRgNpWs9ynHDrgE1oL6Cq"
    "LMJUm7uC0SdSr03RhEq8u9DH4VmMx6UbkJEcMknLfA2FIu0U8eoXCbJKOTByQaLb3tggidwi"
    "X3d5GR1ZyKmAAAAABJRU5ErkJggg=="
)

try:
    _icon_img = tk.PhotoImage(data=_ICON_B64)
    root.iconphoto(True, _icon_img)
except Exception:
    pass
try:
    _base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    _ico = os.path.join(_base, "audiobook-converter.ico")
    if os.path.exists(_ico):
        root.iconbitmap(default=_ico)
except Exception:
    pass

style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", font=("Segoe UI", 10))
style.configure("TButton", font=("Segoe UI", 9))

controls_frame = ttk.Frame(root)
controls_frame.pack(padx=10, pady=(10, 0), fill="x")
ttk.Label(controls_frame, text="Output filename:").grid(row=0, column=0, sticky="w", padx=(0, 5))
output_name_var = tk.StringVar(value="audiobook")
ttk.Entry(controls_frame, textvariable=output_name_var, width=24).grid(row=0, column=1, sticky="ew", padx=(0, 10))
ttk.Label(controls_frame, text="Bitrate:").grid(row=0, column=2, sticky="w", padx=(0, 5))
bitrate_var = tk.StringVar(value="64k")
ttk.Combobox(controls_frame, textvariable=bitrate_var, values=["32k", "48k", "64k", "96k", "128k"],
             width=6, state="readonly").grid(row=0, column=3, sticky="w")
controls_frame.columnconfigure(1, weight=1)

DRAG_TEXT = ("🎧 Drag and drop audio files or a folder here\n"
             "(.mp3 / .m4a / .aac / .flac / .wav)\n\n"
             "Files will be sorted by filename and merged in order.")

drag_label = ttk.Label(root, text=DRAG_TEXT if dnd_available else
                       "Drag-and-drop not available.\nInstall tkinterdnd2.",
                       anchor="center", relief="solid", padding=10,
                       font=("Segoe UI Emoji", 12), justify="center")
drag_label.pack(padx=10, pady=10, fill="both", expand=True, ipady=30)

output_frame = ttk.Frame(root)
progress_bar = ttk.Progressbar(output_frame, orient="horizontal", mode="determinate")
progress_bar.pack(fill="x", padx=10, pady=(0, 5))
progress_bar["maximum"] = 100

output_header = ttk.Frame(output_frame)
output_header.pack(fill="x")
ttk.Label(output_header, text="📋 Conversion Log", anchor="w").pack(side="left", padx=(5,0), pady=2)
ttk.Button(output_header, text="❌", width=3, command=lambda: hide_output(clear=True)).pack(side="right", padx=5, pady=2)

output_text_frame = ttk.Frame(output_frame)
output_text_frame.pack(fill="both", expand=True)
scrollbar = ttk.Scrollbar(output_text_frame)
scrollbar.pack(side="right", fill="y")
output_text = tk.Text(output_text_frame, wrap="word", height=10,
                      yscrollcommand=scrollbar.set, state="disabled")
output_text.pack(side="left", fill="both", expand=True)
scrollbar.config(command=output_text.yview)
output_frame.pack_forget()

start_button = ttk.Button(root, text="▶  Start Conversion", command=lambda: on_start_clicked())
pending_files = []

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def show_output():
    output_frame.pack(padx=10, pady=(0, 10), fill="both", expand=True)

def hide_output(clear=False):
    global pending_files
    output_frame.pack_forget()
    output_text.configure(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.configure(state="disabled")
    if clear:
        progress_bar["value"] = 0
        pending_files = []
        start_button.pack_forget()
        drag_label.config(state="normal", text=DRAG_TEXT)

def write_output(message, replace_last=False):
    show_output()
    output_text.configure(state="normal")
    if replace_last:
        output_text.delete("end-2l", "end-1l")
    output_text.insert("end", message + "\n")
    output_text.configure(state="disabled")
    output_text.see("end")

def update_progress(value):
    root.after(0, lambda: progress_bar.config(value=value))

# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

def run_silent(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)

def check_ffmpeg():
    try:
        run_silent(["ffmpeg", "-version"])
        run_silent(["ffprobe", "-version"])
        return True
    except FileNotFoundError:
        return False

# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

def deduce_output_name(file_paths):
    for tag in ("album", "title"):
        r = run_silent(["ffprobe", "-v", "error",
                        "-show_entries", f"format_tags={tag}",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        file_paths[0]])
        val = r.stdout.strip()
        if val and len(val) > 1:
            safe = "".join(c for c in val if c not in r'\/:*?"<>|').strip()
            if safe:
                return safe
    basenames = [os.path.splitext(os.path.basename(f))[0] for f in file_paths]
    if len(basenames) == 1:
        return basenames[0]
    prefix = os.path.commonprefix(basenames).rstrip(" -_0123456789").strip()
    if len(prefix) >= 3:
        return prefix
    parent = os.path.basename(os.path.dirname(file_paths[0]))
    return parent if parent else "audiobook"

def detect_bitrate(file_path):
    r = run_silent(["ffprobe", "-v", "error",
                    "-show_entries", "format=bit_rate",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    file_path])
    try:
        kbps = int(r.stdout.strip()) // 1000
        valid = [s for s in [32, 48, 64, 96, 128] if s <= kbps] or [32]
        return f"{valid[-1]}k"
    except Exception:
        return "64k"

def get_duration_ms(file_path):
    r = run_silent(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", file_path])
    return int(float(r.stdout.strip()) * 1000)

# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

def convert_to_m4b(file_paths):
    if not check_ffmpeg():
        root.after(0, lambda: messagebox.showerror("ffmpeg Not Found",
            "ffmpeg and ffprobe must be installed and on your PATH.\n\n"
            "Install via: winget install ffmpeg"))
        return

    audio_files = file_paths
    total = len(audio_files)
    start_time = time.time()

    def clean(p):
        return p.replace("\\\\?\\", "")

    clean_dir = clean(os.path.dirname(audio_files[0]))
    out_name = output_name_var.get().strip() or "audiobook"
    bitrate = bitrate_var.get()
    if not out_name.lower().endswith(".m4b"):
        out_name += ".m4b"

    out_path = os.path.join(clean_dir, out_name)
    counter = 1
    base_out = out_path[:-4]
    while os.path.exists(out_path):
        out_path = f"{base_out}-{counter}.m4b"
        counter += 1

    temp_files = []
    meta_txt  = os.path.join(clean_dir, "_m4b_meta.txt")
    files_txt = os.path.join(clean_dir, "_m4b_files.txt")
    temp_concat = os.path.join(clean_dir, "_m4b_concat_temp.m4b")

    root.after(0, lambda: write_output(f"📁 Encoding {total} file(s)...\n"))

    chapter_meta = []
    offset_ms = 0
    errors = []

    for i, path in enumerate(audio_files):
        fname = os.path.basename(path)
        root.after(0, lambda f=fname, idx=i+1, p=int((i/total)*60): (
            write_output(f"  [{idx}/{total}] Encoding: {f}...", replace_last=(idx > 1)),
            update_progress(p)
        ))
        temp_out = os.path.join(clean_dir, f"_m4b_part_{i:04d}.m4a")
        temp_files.append(temp_out)

        proc = run_silent(["ffmpeg", "-y", "-i", clean(path),
                           "-c:a", "aac", "-b:a", bitrate, "-vn", temp_out])
        if proc.returncode != 0:
            errors.append(f"{fname}: {proc.stderr[-300:]}")
            continue

        try:
            dur_ms = get_duration_ms(temp_out)
        except Exception:
            dur_ms = 0

        chapter_meta.append((offset_ms, offset_ms + dur_ms, os.path.splitext(fname)[0]))
        offset_ms += dur_ms
        root.after(0, lambda f=fname, idx=i+1: (
            write_output(f"  [{idx}/{total}] ✅ {f}", replace_last=True)
        ))
        update_progress(int(((i + 1) / total) * 60))

    if errors:
        summary = "\n\n".join(errors[:5])
        root.after(0, lambda s=summary: messagebox.showerror("Encoding Errors",
                                                              f"{len(errors)} file(s) failed:\n\n{s}"))
        _cleanup(*temp_files, meta_txt, files_txt, temp_concat)
        return

    root.after(0, lambda: write_output("\n⏳ Merging files..."))
    update_progress(65)

    with open(files_txt, "w", encoding="utf-8") as f:
        for tf in temp_files:
            f.write(f"file '{tf.replace(chr(92), '/')}'\n")

    proc2 = run_silent(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", files_txt, "-c", "copy", temp_concat])
    if proc2.returncode != 0:
        root.after(0, lambda e=proc2.stderr[-800:]: messagebox.showerror("ffmpeg Error", f"Merge failed:\n\n{e}"))
        _cleanup(*temp_files, meta_txt, files_txt, temp_concat)
        return

    update_progress(75)
    root.after(0, lambda: write_output("⏳ Injecting chapters..."))

    with open(meta_txt, "w", encoding="utf-8") as f:
        f.write(";FFMETADATA1\n")
        for s_ms, e_ms, title in chapter_meta:
            f.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={s_ms}\nEND={e_ms}\ntitle={title}\n\n")

    update_progress(85)

    proc3 = run_silent(["ffmpeg", "-y",
                        "-i", temp_concat, "-i", meta_txt,
                        "-map_metadata", "1",
                        "-metadata", f"album={out_name[:-4]}",
                        "-codec", "copy", out_path])
    if proc3.returncode != 0:
        root.after(0, lambda e=proc3.stderr[-800:]: messagebox.showerror("ffmpeg Error", f"Chapter mux failed:\n\n{e}"))
        _cleanup(*temp_files, meta_txt, files_txt, temp_concat)
        return

    update_progress(100)
    elapsed = time.time() - start_time
    mins, secs = divmod(int(elapsed), 60)
    time_str = f"{mins}m {secs}s" if mins else f"{secs}s"
    size_str = f"{round(os.path.getsize(out_path) / (1024*1024), 1)} MB"
    root.after(0, lambda: write_output(
        f"\n✅ Done! → {os.path.basename(out_path)} ({size_str})\n"
        f"📂 Saved to: {os.path.dirname(out_path)}\n"
        f"⏱️ Completed in {time_str}"
    ))
    root.after(1500, lambda: update_progress(0))
    _cleanup(*temp_files, meta_txt, files_txt, temp_concat)

def _cleanup(*paths):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Start / background thread
# ---------------------------------------------------------------------------

def on_start_clicked():
    global pending_files
    if not pending_files:
        return
    files = pending_files[:]
    start_button.pack_forget()
    drag_label.config(state="disabled", text="⏳ Converting...")
    output_text.configure(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.configure(state="disabled")
    progress_bar["value"] = 0
    threading.Thread(target=lambda: convert_in_background(files), daemon=True).start()

def convert_in_background(files):
    try:
        convert_to_m4b(files)
    finally:
        root.after(0, lambda: drag_label.config(state="normal", text=DRAG_TEXT))

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def normalize_path(p):
    p = p.replace('/', os.sep)
    p = os.path.normpath(p)
    if sys.platform == "win32" and not p.startswith("\\\\"):
        p = "\\\\?\\" + p
    return p

def parse_dropped_paths(data):
    paths = []
    data = data.strip()
    i = 0
    while i < len(data):
        if data[i] == '{':
            end = data.find('}', i)
            if end != -1:
                paths.append(data[i+1:end].strip())
                i = end + 1
            else:
                paths.append(data[i+1:].strip())
                break
        elif data[i] == ' ':
            i += 1
        else:
            end = data.find(' ', i)
            if end == -1:
                paths.append(data[i:].strip())
                break
            else:
                paths.append(data[i:end].strip())
                i = end + 1
    return [p for p in paths if p]

# ---------------------------------------------------------------------------
# Drag-and-drop  (single clean handler — no duplicate code below this)
# ---------------------------------------------------------------------------

def drop_event_handler(event):
    global pending_files

    try:
        raw = root.tk.call('set', '::tkdnd::_dropped_data')
    except Exception:
        raw = event.data

    raw_paths = parse_dropped_paths(raw)
    hide_output(clear=True)

    if not raw_paths:
        write_output("⚠️ No paths parsed from drop data.")
        write_output(f"   Raw: {raw[:300]}")
        show_output()
        return

    all_files = []
    debug_lines = []
    for path in raw_paths:
        norm = normalize_path(path)
        is_file = os.path.isfile(norm)
        is_dir  = os.path.isdir(norm)
        tag = "FILE" if is_file else "DIR" if is_dir else "MISS"
        debug_lines.append(f"  {tag}: {path[:120]}")
        if is_file:
            if os.path.splitext(path)[1].lower() in SUPPORTED_FORMATS:
                all_files.append(norm)
        elif is_dir:
            for dirpath, _, filenames in os.walk(norm):
                for filename in filenames:
                    if os.path.splitext(filename)[1].lower() in SUPPORTED_FORMATS:
                        all_files.append(os.path.join(dirpath, filename))

    if not all_files:
        write_output("⚠️ No supported audio files found. Debug info:")
        for line in debug_lines:
            write_output(line)
        show_output()
        drag_label.config(text=DRAG_TEXT)
        return

    pending_files = sorted(all_files)
    drag_label.config(text="🔍 Detecting metadata...")
    write_output(f"📁 {len(pending_files)} file(s) found — reading metadata...\n")
    show_output()

    def probe_and_stage():
        suggested  = deduce_output_name(pending_files)
        detected_br = detect_bitrate(pending_files[0])

        def update_ui():
            output_name_var.set(suggested)
            bitrate_var.set(detected_br)
            drag_label.config(text=DRAG_TEXT)
            output_text.configure(state="normal")
            output_text.delete("1.0", tk.END)
            output_text.configure(state="disabled")
            write_output(f"📁 {len(pending_files)} file(s) queued — review order below:\n")
            for i, f in enumerate(pending_files):
                write_output(f"  {i+1:>3}. {os.path.basename(f)}")
            write_output(f"\n🎵 Detected bitrate: {detected_br}  |  Name: \"{suggested}\"")
            write_output("\n✅ Order look correct? Hit Start — or ❌ to cancel and re-drop.")
            start_button.pack(padx=10, pady=(0, 4), fill="x")
            start_button.lift()

        root.after(0, update_ui)

    threading.Thread(target=probe_and_stage, daemon=True).start()

# ---------------------------------------------------------------------------
# Bind and launch
# ---------------------------------------------------------------------------

if dnd_available:
    drag_label.drop_target_register(tkdnd.DND_FILES)
    drag_label.dnd_bind('<<Drop>>', drop_event_handler)
else:
    drag_label.config(text="⚠️ Install tkinterdnd2 for drag-and-drop.\n\npip install tkinterdnd2")

if __name__ == "__main__":
    try:
        root.mainloop()
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        with open("easym4b-error.log", "w") as f:
            f.write(trace)
        messagebox.showerror("Startup Crash", f"{type(e).__name__}: {e}")
