import os
import sys
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
root.geometry("520x500")
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

# --- Output Helpers ---
def show_output():
    output_frame.pack(padx=10, pady=(0, 10), fill="both", expand=True)

def hide_output(clear=False):
    output_frame.pack_forget()
    output_text.configure(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.configure(state="disabled")
    if clear:
        progress_bar["value"] = 0

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

# --- ffmpeg check ---
def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

# --- Get audio duration in milliseconds ---
def get_duration_ms(file_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", file_path],
        capture_output=True, text=True
    )
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

    # Filter and sort files
    audio_files = sorted(
        [f for f in file_paths if os.path.splitext(f)[1].lower() in SUPPORTED_FORMATS]
    )

    if not audio_files:
        root.after(0, lambda: messagebox.showinfo("No Supported Files", "No supported audio files were found."))
        return

    output_dir = os.path.dirname(audio_files[0])
    out_name = output_name_var.get().strip() or "audiobook"
    bitrate = bitrate_var.get()

    # Ensure .m4b extension
    if not out_name.lower().endswith(".m4b"):
        out_name += ".m4b"

    out_path = os.path.join(output_dir, out_name)
    counter = 1
    base_out = out_path.replace(".m4b", "")
    while os.path.exists(out_path):
        out_path = f"{base_out}-{counter}.m4b"
        counter += 1

    temp_concat = os.path.join(output_dir, "_m4b_concat_temp.m4b")
    files_txt = os.path.join(output_dir, "_m4b_files.txt")
    meta_txt = os.path.join(output_dir, "_m4b_meta.txt")

    root.after(0, lambda: write_output(f"📁 Found {len(audio_files)} file(s). Sorting by filename..."))

    for i, f in enumerate(audio_files):
        root.after(0, lambda fn=os.path.basename(f), idx=i+1: write_output(f"  {idx}. {fn}"))

    root.after(0, lambda: write_output("\n⏳ Step 1/3: Building file list..."))
    update_progress(5)

    # Write files.txt (escape single quotes for ffmpeg)
    with open(files_txt, "w", encoding="utf-8") as f:
        for path in audio_files:
            escaped = path.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

    root.after(0, lambda: write_output("⏳ Step 2/3: Encoding to AAC/M4B (this may take a moment)..."))
    update_progress(15)

    # Concat + encode
    encode_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", files_txt,
        "-c:a", "aac", "-b:a", bitrate,
        "-vn",
        temp_concat
    ]

    proc = subprocess.run(encode_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = proc.stderr[-800:] if proc.stderr else "Unknown error"
        root.after(0, lambda e=err: messagebox.showerror("ffmpeg Error", f"Encoding failed:\n\n{e}"))
        _cleanup(files_txt, meta_txt, temp_concat)
        return

    update_progress(70)
    root.after(0, lambda: write_output("⏳ Step 3/3: Building chapter metadata..."))

    # Build chapter metadata
    offset = 0
    meta_lines = [";FFMETADATA1\n"]
    for path in audio_files:
        try:
            dur_ms = get_duration_ms(path)
        except Exception:
            dur_ms = 0
        end = offset + dur_ms
        chapter_title = os.path.splitext(os.path.basename(path))[0]
        meta_lines.append(
            f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={offset}\nEND={end}\ntitle={chapter_title}\n\n"
        )
        offset = end

    with open(meta_txt, "w", encoding="utf-8") as f:
        f.writelines(meta_lines)

    update_progress(80)

    # Mux chapters into final file
    mux_cmd = [
        "ffmpeg", "-y",
        "-i", temp_concat,
        "-i", meta_txt,
        "-map_metadata", "1",
        "-codec", "copy",
        out_path
    ]

    proc2 = subprocess.run(mux_cmd, capture_output=True, text=True)
    if proc2.returncode != 0:
        err = proc2.stderr[-800:] if proc2.stderr else "Unknown error"
        root.after(0, lambda e=err: messagebox.showerror("ffmpeg Error", f"Chapter muxing failed:\n\n{e}"))
        _cleanup(files_txt, meta_txt, temp_concat)
        return

    update_progress(100)
    out_size = os.path.getsize(out_path)
    size_str = f"{round(out_size / (1024*1024), 1)} MB"
    root.after(0, lambda: write_output(f"\n✅ Done! → {os.path.basename(out_path)} ({size_str})\n📂 Saved to: {output_dir}"))
    root.after(1000, lambda: update_progress(0))

    _cleanup(files_txt, meta_txt, temp_concat)

def _cleanup(*paths):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

# --- Threaded handler ---
def convert_in_background(files):
    try:
        convert_to_m4b(files)
    finally:
        root.after(0, lambda: drag_label.config(
            state="normal",
            text="🎧 Drag and drop audio files here\n(.mp3 / .m4a / .aac / .flac / .wav)\n\nFiles will be sorted by filename and merged in order."
        ))

# --- Drag-and-drop handler ---
def drop_event_handler(event):
    files_or_dirs = root.tk.splitlist(event.data)
    if not files_or_dirs:
        return

    all_files = []
    for path in files_or_dirs:
        if os.path.isfile(path):
            all_files.append(path)
        elif os.path.isdir(path):
            for dirpath, _, filenames in os.walk(path):
                for filename in filenames:
                    full_path = os.path.join(dirpath, filename)
                    if os.path.splitext(full_path)[1].lower() in SUPPORTED_FORMATS:
                        all_files.append(full_path)

    if not all_files:
        messagebox.showinfo("No Supported Files", "No supported audio files found.")
        return

    hide_output(clear=True)
    drag_label.config(state="disabled", text="⏳ Converting...")
    write_output("⏳ Starting conversion...")
    progress_bar["value"] = 0

    threading.Thread(target=lambda: convert_in_background(all_files), daemon=True).start()

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