import os
import sys
import re
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# --- App Config ---
SUPPORTED_FORMATS = (".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg")

# --- Attempt tkinterdnd2 ---
try:
    import tkinterdnd2 as tkdnd
    root = tkdnd.TkinterDnD.Tk()
    dnd_available = True
except ImportError:
    root = tk.Tk()
    dnd_available = False

# --- GUI Setup ---
root.title("Easy M4B Converter")
root.geometry("800x600")
root.minsize(380, 500)
root.resizable(True, True)

# --- Style ---
style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", font=("Segoe UI", 10))
style.configure("TButton", font=("Segoe UI", 9))

# --- Top controls frame ---
controls_frame = ttk.Frame(root)
controls_frame.pack(padx=10, pady=(10, 0), fill="x")

# Output name
ttk.Label(controls_frame, text="Output filename:").grid(row=0, column=0, sticky="w", padx=(0, 5))
output_name_var = tk.StringVar(value="audiobook")
output_entry = ttk.Entry(controls_frame, textvariable=output_name_var, width=24)
output_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))

# Bitrate
ttk.Label(controls_frame, text="Bitrate:").grid(row=0, column=2, sticky="w", padx=(0, 5))
bitrate_var = tk.StringVar(value="64k")
bitrate_combo = ttk.Combobox(controls_frame, textvariable=bitrate_var, values=["32k", "48k", "64k", "96k", "128k"], width=6, state="readonly")
bitrate_combo.grid(row=0, column=3, sticky="w")

controls_frame.columnconfigure(1, weight=1)

# --- Drag area ---
drag_label = ttk.Label(
    root,
    text="🎧 Drag and drop audio files here\n(.mp3 / .m4a / .aac / .flac / .wav)\n\nFiles will be sorted by filename and merged in order." if dnd_available else
    "Drag-and-drop not available.\nInstall tkinterdnd2 for full functionality.",
    anchor="center",
    relief="solid",
    padding=10,
    font=("Segoe UI Emoji", 12),
    justify="center"
)
drag_label.pack(padx=10, pady=10, fill="both", expand=True, ipady=30)

# --- Output frame (initially hidden) ---
output_frame = ttk.Frame(root)

# Progress bar
progress_bar = ttk.Progressbar(output_frame, orient="horizontal", mode="determinate")
progress_bar.pack(fill="x", padx=10, pady=(0, 5))
progress_bar["maximum"] = 100
progress_bar["value"] = 0

# Header with close button
output_header = ttk.Frame(output_frame)
output_header.pack(fill="x")

output_title = ttk.Label(output_header, text="📋 Conversion Log", anchor="w")
output_title.pack(side="left", padx=(5, 0), pady=2)

close_button = ttk.Button(output_header, text="❌", width=3, command=lambda: hide_output(clear=True))
close_button.pack(side="right", padx=5, pady=2)

# Scrollable text log
output_text_frame = ttk.Frame(output_frame)
output_text_frame.pack(fill="both", expand=True)

scrollbar = ttk.Scrollbar(output_text_frame)
scrollbar.pack(side="right", fill="y")

output_text = tk.Text(output_text_frame, wrap="word", height=10, yscrollcommand=scrollbar.set, state="disabled")
output_text.pack(side="left", fill="both", expand=True)

scrollbar.config(command=output_text.yview)
output_frame.pack_forget()

# --- Start button (shown after drop, before processing) ---
start_button = ttk.Button(root, text="▶  Start Conversion", command=lambda: on_start_clicked())
# packed dynamically, hidden by default

# --- State ---
pending_files = []

# --- Output Helpers ---
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
        drag_label.config(
            state="normal",
            text="🎧 Drag and drop audio files here\n(.mp3 / .m4a / .aac / .flac / .wav)\n\nFiles will be sorted by filename and merged in order."
        )

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

# --- Suppress console window on Windows ---
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

def run_silent(cmd):
    """Run a subprocess with no console window, return CompletedProcess."""
    return subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)

# --- ffmpeg check ---
def check_ffmpeg():
    try:
        run_silent(["ffmpeg", "-version"])
        run_silent(["ffprobe", "-version"])
        return True
    except FileNotFoundError:
        return False

# --- Deduce a good output name from files ---
def deduce_output_name(file_paths):
    # 1. Try album tag from first file (most reliable for audiobook rips)
    for tag in ("album", "title"):
        result = run_silent([
            "ffprobe", "-v", "error",
            "-show_entries", f"format_tags={tag}",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_paths[0]
        ])
        val = result.stdout.strip()
        if val and len(val) > 1:
            # Sanitize for use as filename
            safe = "".join(c for c in val if c not in r'\/:*?"<>|').strip()
            if safe:
                return safe

    # 2. Fall back to longest common prefix of filenames
    basenames = [os.path.splitext(os.path.basename(f))[0] for f in file_paths]
    if len(basenames) == 1:
        return basenames[0]

    prefix = os.path.commonprefix(basenames)

    # Strip trailing separators/numbers/whitespace (e.g. "BookName - 0" → "BookName")
    prefix = prefix.rstrip(" -_0123456789").strip()

    if len(prefix) >= 3:
        return prefix

    # 3. Last resort: name of the parent folder
    parent = os.path.basename(os.path.dirname(file_paths[0]))
    if parent:
        return parent

    return "audiobook"

# --- Detect source bitrate ---
def detect_bitrate(file_path):
    result = run_silent([
        "ffprobe", "-v", "error",
        "-show_entries", "format=bit_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ])
    try:
        bps = int(result.stdout.strip())
        kbps = bps // 1000
        steps = [32, 48, 64, 96, 128]
        # Snap to nearest step — never encode higher than source
        nearest = min(steps, key=lambda s: abs(s - kbps))
        capped  = min(nearest, kbps)  # never exceed source bitrate
        # Pick the highest step that is <= capped
        valid = [s for s in steps if s <= capped] or [32]
        return f"{valid[-1]}k"
    except Exception:
        return "64k"

# --- Get audio duration in milliseconds ---
def get_duration_ms(file_path):
    result = run_silent([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ])
    return int(float(result.stdout.strip()) * 1000)

# --- Main conversion logic ---
def convert_to_m4b(file_paths):
    if not check_ffmpeg():
        messagebox.showerror(
            "ffmpeg Not Found",
            "ffmpeg and ffprobe must be installed and available on your PATH.\n\n"
            "Download from: https://ffmpeg.org/download.html\n"
            "Or on Windows: winget install ffmpeg"
        )
        return

    import time
    start_time = time.time()

    audio_files = file_paths  # already filtered and sorted at drop time

    if not audio_files:
        root.after(0, lambda: messagebox.showinfo("No Supported Files", "No supported audio files were found."))
        return

    total = len(audio_files)
    output_dir = os.path.dirname(audio_files[0])
    out_name = output_name_var.get().strip() or "audiobook"
    bitrate = bitrate_var.get()

    if not out_name.lower().endswith(".m4b"):
        out_name += ".m4b"

    out_path = os.path.join(output_dir, out_name)
    counter = 1
    base_out = out_path[:-4]  # strip .m4b
    while os.path.exists(out_path):
        out_path = f"{base_out}-{counter}.m4b"
        counter += 1

    temp_dir = output_dir
    temp_files = []
    meta_txt = os.path.join(temp_dir, "_m4b_meta.txt")
    files_txt = os.path.join(temp_dir, "_m4b_files.txt")
    temp_concat = os.path.join(temp_dir, "_m4b_concat_temp.m4b")

    root.after(0, lambda: write_output(f"📁 Found {total} file(s) — encoding each file...\n"))

    # --- Step 1: Encode each file individually to AAC so progress is trackable ---
    chapter_meta = []
    offset_ms = 0
    errors = []

    for i, path in enumerate(audio_files):
        fname = os.path.basename(path)
        pct = int((i / total) * 60)  # steps 0–60% during encoding
        root.after(0, lambda f=fname, idx=i+1, p=pct: (
            write_output(f"  [{idx}/{total}] Encoding: {f}...", replace_last=(idx > 1)),
            update_progress(p)
        ))

        temp_out = os.path.join(temp_dir, f"_m4b_part_{i:04d}.m4a")
        temp_files.append(temp_out)

        encode_cmd = [
            "ffmpeg", "-y", "-i", path,
            "-c:a", "aac", "-b:a", bitrate, "-vn",
            temp_out
        ]
        proc = run_silent(encode_cmd)
        if proc.returncode != 0:
            errors.append(f"{fname}: {proc.stderr[-300:]}")
            continue

        try:
            dur_ms = get_duration_ms(temp_out)
        except Exception:
            dur_ms = 0

        chapter_title = os.path.splitext(fname)[0]
        chapter_meta.append((offset_ms, offset_ms + dur_ms, chapter_title))
        offset_ms += dur_ms

        root.after(0, lambda f=fname, idx=i+1: (
            write_output(f"  [{idx}/{total}] ✅ {f}", replace_last=True)
        ))
        update_progress(int(((i + 1) / total) * 60))

    if errors:
        summary = "\n\n".join(errors[:5])
        root.after(0, lambda s=summary: messagebox.showerror("Encoding Errors", f"{len(errors)} file(s) failed:\n\n{s}"))
        _cleanup(*temp_files, meta_txt, files_txt, temp_concat)
        return

    # --- Step 2: Write concat list ---
    root.after(0, lambda: write_output("\n⏳ Merging files..."))
    update_progress(65)

    with open(files_txt, "w", encoding="utf-8") as f:
        for tf in temp_files:
            escaped = tf.replace("\\", "/")
            f.write(f"file '{escaped}'\n")

    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", files_txt,
        "-c", "copy",
        temp_concat
    ]
    proc2 = run_silent(concat_cmd)
    if proc2.returncode != 0:
        err = proc2.stderr[-800:]
        root.after(0, lambda e=err: messagebox.showerror("ffmpeg Error", f"Merge failed:\n\n{e}"))
        _cleanup(*temp_files, meta_txt, files_txt, temp_concat)
        return

    update_progress(75)

    # --- Step 3: Build chapter metadata ---
    root.after(0, lambda: write_output("⏳ Injecting chapters..."))
    meta_lines = [";FFMETADATA1\n"]
    for start_ms, end_ms, title in chapter_meta:
        meta_lines.append(
            f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={start_ms}\nEND={end_ms}\ntitle={title}\n\n"
        )
    with open(meta_txt, "w", encoding="utf-8") as f:
        f.writelines(meta_lines)

    update_progress(85)

    mux_cmd = [
        "ffmpeg", "-y",
        "-i", temp_concat,
        "-i", meta_txt,
        "-map_metadata", "1",
        "-metadata", f"album={out_name[:-4]}",
        "-codec", "copy",
        out_path
    ]
    proc3 = run_silent(mux_cmd)
    if proc3.returncode != 0:
        err = proc3.stderr[-800:]
        root.after(0, lambda e=err: messagebox.showerror("ffmpeg Error", f"Chapter mux failed:\n\n{e}"))
        _cleanup(*temp_files, meta_txt, files_txt, temp_concat)
        return

    update_progress(100)
    elapsed = time.time() - start_time
    mins, secs = divmod(int(elapsed), 60)
    time_str = f"{mins}m {secs}s" if mins else f"{secs}s"
    out_size = os.path.getsize(out_path)
    size_str = f"{round(out_size / (1024*1024), 1)} MB"
    root.after(0, lambda: write_output(
        f"\n✅ Done! → {os.path.basename(out_path)} ({size_str})\n"
        f"📂 Saved to: {output_dir}\n"
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

# --- Start button handler ---
def on_start_clicked():
    global pending_files
    if not pending_files:
        return
    files = pending_files[:]
    start_button.pack_forget()
    drag_label.config(state="disabled", text="⏳ Converting...")
    # Clear log and restart with conversion
    output_text.configure(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.configure(state="disabled")
    progress_bar["value"] = 0
    threading.Thread(target=lambda: convert_in_background(files), daemon=True).start()

# --- Threaded handler ---
def convert_in_background(files):
    try:
        convert_to_m4b(files)
    finally:
        root.after(0, lambda: drag_label.config(
            state="normal",
            text="🎧 Drag and drop audio files here\n(.mp3 / .m4a / .aac / .flac / .wav)\n\nFiles will be sorted by filename and merged in order."
        ))

# --- Parse dropped file paths (handles Windows curly-brace wrapping) ---
def parse_dropped_paths(data):
    """tkinterdnd2 on Windows wraps space-containing paths in {curly braces}."""
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
                # Unmatched brace, take rest
                paths.append(data[i+1:].strip())
                break
        elif data[i] == ' ':
            i += 1
        else:
            # Plain path with no spaces (no braces)
            end = data.find(' ', i)
            if end == -1:
                paths.append(data[i:].strip())
                break
            else:
                paths.append(data[i:end].strip())
                i = end + 1
    return [p for p in paths if p]

# --- Drag-and-drop handler ---
def drop_event_handler(event):
    global pending_files
    raw_paths = parse_dropped_paths(event.data)

    hide_output(clear=True)

    if not raw_paths:
        write_output("⚠️ No paths parsed from drop data.")
        write_output(f"   Raw: {event.data[:300]}")
        show_output()
        return

    all_files = []
    debug_lines = []
    for path in raw_paths:
        path = os.path.normpath(path)
        is_file = os.path.isfile(path)
        is_dir  = os.path.isdir(path)
        exists  = os.path.exists(path)
        debug_lines.append(f"  PATH: {path}")
        debug_lines.append(f"    exists={exists}  isfile={is_file}  isdir={is_dir}")
        if is_file:
            all_files.append(path)
        elif is_dir:
            for dirpath, _, filenames in os.walk(path):
                for filename in filenames:
                    full_path = os.path.join(dirpath, filename)
                    if os.path.splitext(full_path)[1].lower() in SUPPORTED_FORMATS:
                        all_files.append(full_path)

    if not all_files:
        write_output("⚠️ No supported audio files found. Debug info:")
        for line in debug_lines:
            write_output(line)
        show_output()
        drag_label.config(
            text="🎧 Drag and drop audio files here\n(.mp3 / .m4a / .aac / .flac / .wav)\n\nFiles will be sorted by filename and merged in order."
        )
        return

    # Sort and stage
    pending_files = sorted(
        [f for f in all_files if os.path.splitext(f)[1].lower() in SUPPORTED_FORMATS]
    )

    if not pending_files:
        write_output("⚠️ Files found but none matched supported formats.")
        show_output()
        return

    drag_label.config(text="🔍 Detecting metadata...")
    write_output(f"📁 {len(pending_files)} file(s) found — reading metadata...\n")
    show_output()

    def probe_and_stage():
        suggested = deduce_output_name(pending_files)
        detected_br = detect_bitrate(pending_files[0])

        def update_ui():
            output_name_var.set(suggested)
            bitrate_var.set(detected_br)
            drag_label.config(
                text="🎧 Drag and drop audio files here\n(.mp3 / .m4a / .aac / .flac / .wav)\n\nFiles will be sorted by filename and merged in order."
            )
            output_text.configure(state="normal")
            output_text.delete("1.0", tk.END)
            output_text.configure(state="disabled")
            write_output(f"📁 {len(pending_files)} file(s) queued — review order below:\n")
            for i, f in enumerate(pending_files):
                write_output(f"  {i+1:>3}. {os.path.basename(f)}")
            write_output(f"\n🎵 Detected bitrate: {detected_br} \nName: \"{suggested}\"")
            write_output("\n✅ Order look correct? Hit Start — or ❌ to cancel and re-drop.")
            start_button.pack(padx=10, pady=(0, 4), fill="x")
            start_button.lift()

        root.after(0, update_ui)

    threading.Thread(target=probe_and_stage, daemon=True).start()

# --- Bind drag-and-drop if available ---
if dnd_available:
    drag_label.drop_target_register(tkdnd.DND_FILES)
    drag_label.dnd_bind('<<Drop>>', drop_event_handler)
else:
    drag_label.config(
        text="⚠️ Install tkinterdnd2 for drag-and-drop support.\n\npip install tkinterdnd2"
    )

# --- Launch ---
if __name__ == "__main__":
    try:
        root.mainloop()
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        with open("easym4b-error.log", "w") as f:
            f.write(trace)
        messagebox.showerror("Startup Crash", f"{type(e).__name__}: {e}")