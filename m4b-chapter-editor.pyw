import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

try:
    import tkinterdnd2 as tkdnd
    root = tkdnd.TkinterDnD.Tk()
    dnd_available = True
except ImportError:
    root = tk.Tk()
    dnd_available = False

root.title("M4B Chapter Editor")
root.geometry("760x620")
root.minsize(480, 520)
root.resizable(True, True)

try:
    _base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    for _icon_name in ("audiobook-converter2.ico", "audiobook-converter.ico"):
        _ico = os.path.join(_base, _icon_name)
        if os.path.exists(_ico):
            root.iconbitmap(default=_ico)
            break
except Exception:
    pass

style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", font=("Segoe UI", 10))
style.configure("TButton", font=("Segoe UI", 9))

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

pending_file = ""
pending_duration_ms = 0
pending_chapter_count = None
is_processing = False

file_name_var = tk.StringVar(value="No file loaded")
duration_var = tk.StringVar(value="--:--:--")
chapter_count_var = tk.StringVar(value="Unknown")
minutes_var = tk.StringVar(value="15")
manual_duration_hours_var = tk.StringVar(value="")
manual_duration_minutes_var = tk.StringVar(value="")


def run_silent(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)


def check_ffmpeg():
    try:
        run_silent(["ffmpeg", "-version"])
        run_silent(["ffprobe", "-version"])
        return True
    except FileNotFoundError:
        return False


def show_output():
    output_frame.pack(padx=10, pady=(0, 10), fill="both", expand=True)


def hide_output(clear=False):
    global pending_file, pending_duration_ms, pending_chapter_count
    output_frame.pack_forget()
    output_text.configure(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.configure(state="disabled")
    if clear:
        progress_bar["value"] = 0
        pending_file = ""
        pending_duration_ms = 0
        pending_chapter_count = None
        file_name_var.set("No file loaded")
        duration_var.set("--:--:--")
        chapter_count_var.set("Unknown")
        manual_duration_hours_var.set("")
        manual_duration_minutes_var.set("")
        set_button.config(state="disabled")
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


def clean_path(path):
    return path.replace("\\\\?\\", "")


def normalize_path(path):
    path = path.replace("/", os.sep)
    path = os.path.normpath(path)
    if sys.platform == "win32" and not path.startswith("\\\\"):
        path = "\\\\?\\" + path
    return path


def parse_dropped_paths(data):
    paths = []
    data = data.strip()
    index = 0
    while index < len(data):
        if data[index] == "{":
            end = data.find("}", index)
            if end != -1:
                paths.append(data[index + 1:end].strip())
                index = end + 1
            else:
                paths.append(data[index + 1:].strip())
                break
        elif data[index] == " ":
            index += 1
        else:
            end = data.find(" ", index)
            if end == -1:
                paths.append(data[index:].strip())
                break
            paths.append(data[index:end].strip())
            index = end + 1
    return [path for path in paths if path]


def format_duration(ms):
    total_seconds = max(0, int(ms // 1000))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def get_m4b_info(file_path):
    result = run_silent([
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_chapters",
        file_path,
    ])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed to read file metadata.")
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe returned invalid metadata.") from exc

    chapters = data.get("chapters", [])
    if not isinstance(chapters, list):
        chapters = []

    duration_raw = data.get("format", {}).get("duration", "0")
    try:
        duration_ms = int(float(duration_raw) * 1000)
    except (TypeError, ValueError):
        duration_ms = 0

    return {
        "duration_ms": duration_ms,
        "chapter_count": len(chapters),
    }


def get_source_tags(file_path):
    result = run_silent([
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_entries", "format_tags",
        file_path,
    ])
    if result.returncode != 0:
        return {}
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {}
    tags = data.get("format", {}).get("tags", {})
    return tags if isinstance(tags, dict) else {}


def escape_ffmetadata_value(value):
    # Escape backslashes/newlines for ffmetadata parser safety.
    return str(value).replace("\\", "\\\\").replace("\n", "\\n")


def sanitize(text):
    return "".join(char for char in text if char not in r'\\/:*?"<>|').strip()


def build_output_path(file_path, interval_minutes):
    clean_input = clean_path(file_path)
    folder = os.path.dirname(clean_input)
    stem, _ = os.path.splitext(os.path.basename(clean_input))
    candidate = os.path.join(folder, sanitize(f"{stem} - chapters-{interval_minutes:02d}m") + ".m4b")
    counter = 1
    base_name = candidate[:-4]
    while os.path.exists(candidate):
        candidate = f"{base_name}-{counter}.m4b"
        counter += 1
    return candidate


def build_chapters(duration_ms, interval_minutes):
    if duration_ms <= 0:
        raise ValueError("Could not determine the file duration.")

    interval_ms = interval_minutes * 60 * 1000
    starts = list(range(0, duration_ms, interval_ms))
    total = len(starts)
    width = max(2, len(str(total)))
    chapters = []
    for index, start_ms in enumerate(starts, start=1):
        end_ms = min(start_ms + interval_ms, duration_ms)
        chapters.append((start_ms, end_ms, f"Chapter {index:0{width}d}"))
    return chapters


def write_ffmetadata(meta_path, chapters, tags=None):
    with open(meta_path, "w", encoding="utf-8") as handle:
        handle.write(";FFMETADATA1\n")
        if tags:
            for key, value in tags.items():
                if key is None or value is None:
                    continue
                key_text = str(key).strip()
                if not key_text:
                    continue
                handle.write(f"{key_text}={escape_ffmetadata_value(value)}\n")
            handle.write("\n")
        for start_ms, end_ms, title in chapters:
            handle.write(
                f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={start_ms}\nEND={end_ms}\ntitle={title}\n\n"
            )


def cleanup(*paths):
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def set_chapters(file_path, duration_ms, interval_minutes):
    output_path = build_output_path(file_path, interval_minutes)
    meta_path = os.path.join(os.path.dirname(clean_path(file_path)), "_chapter_editor_meta.txt")
    chapters = build_chapters(duration_ms, interval_minutes)
    source_tags = get_source_tags(clean_path(file_path))
    write_ffmetadata(meta_path, chapters, tags=source_tags)

    command = [
        "ffmpeg", "-y",
        "-i", clean_path(file_path),
        "-i", meta_path,
        # Keep audiobook audio and optional cover art, but drop subtitle/data streams
        # that can break ipod/m4b muxing when stream-copied.
        "-map", "0:a",
        "-map", "0:v?",
        # Import chapter and tag metadata from ffmetadata input.
        "-map_metadata", "1",
        "-codec", "copy",
        output_path,
    ]
    result = run_silent(command)
    if result.returncode != 0:
        cleanup(meta_path, output_path)
        raise RuntimeError(result.stderr[-800:] or "ffmpeg failed to write the updated file.")

    try:
        output_info = get_m4b_info(output_path)
    finally:
        cleanup(meta_path)
    return output_path, len(chapters), output_info["chapter_count"]


def validate_minutes(*_):
    value = minutes_var.get().strip()
    if not value:
        return True
    if not value.isdigit():
        return False
    return len(value) <= 2


def normalize_minutes_field(_event=None):
    value = minutes_var.get().strip()
    if not value:
        minutes_var.set("15")
        return
    try:
        minutes = int(value)
    except ValueError:
        minutes_var.set("15")
        return
    minutes = max(1, min(60, minutes))
    minutes_var.set(f"{minutes:02d}")


def validate_manual_hours(*_):
    value = manual_duration_hours_var.get().strip()
    if not value:
        return True
    if not value.isdigit():
        return False
    return len(value) <= 3


def validate_manual_minutes(*_):
    value = manual_duration_minutes_var.get().strip()
    if not value:
        return True
    if not value.isdigit():
        return False
    return len(value) <= 2


def normalize_manual_duration_fields(_event=None):
    raw_hours = manual_duration_hours_var.get().strip()
    raw_minutes = manual_duration_minutes_var.get().strip()

    hours = int(raw_hours) if raw_hours.isdigit() else 0
    minutes = int(raw_minutes) if raw_minutes.isdigit() else 0

    if minutes > 59:
        minutes = 59

    manual_duration_hours_var.set(str(max(0, hours)) if raw_hours or raw_minutes else "")
    manual_duration_minutes_var.set(f"{minutes:02d}" if raw_hours or raw_minutes else "")


def get_effective_duration_ms():
    if pending_duration_ms > 0:
        return pending_duration_ms, False, 0, 0

    raw_hours = manual_duration_hours_var.get().strip()
    raw_minutes = manual_duration_minutes_var.get().strip()
    if not raw_hours and not raw_minutes:
        raise ValueError("Duration could not be detected. Enter Manual Duration hours and/or minutes.")

    if raw_hours and not raw_hours.isdigit():
        raise ValueError("Manual Duration hours must be a whole number.")
    if raw_minutes and not raw_minutes.isdigit():
        raise ValueError("Manual Duration minutes must be a whole number.")

    manual_hours = int(raw_hours) if raw_hours else 0
    manual_minutes = int(raw_minutes) if raw_minutes else 0

    if manual_minutes > 59:
        raise ValueError("Manual Duration minutes must be between 00 and 59.")

    total_minutes = (manual_hours * 60) + manual_minutes
    if total_minutes <= 0:
        raise ValueError("Manual Duration must be greater than 0 minutes.")

    return total_minutes * 60 * 1000, True, manual_hours, manual_minutes


def set_processing_state(active, status_text=None):
    global is_processing
    is_processing = active
    set_button.config(state="disabled" if active or not pending_file else "normal")
    drag_label.config(state="disabled" if active else "normal")
    if status_text:
        drag_label.config(text=status_text)
    elif not active:
        drag_label.config(text=DRAG_TEXT)


def probe_file(file_path):
    global pending_file, pending_duration_ms, pending_chapter_count
    try:
        info = get_m4b_info(clean_path(file_path))
    except Exception as exc:
        root.after(0, lambda err=str(exc): (
            write_output(f"⚠️ {err}"),
            set_processing_state(False)
        ))
        return

    pending_file = file_path
    pending_duration_ms = info["duration_ms"]
    pending_chapter_count = info["chapter_count"]

    def update_ui():
        file_name_var.set(os.path.basename(clean_path(file_path)))
        duration_var.set(format_duration(pending_duration_ms) if pending_duration_ms > 0 else "Unknown")
        chapter_label = "chapter" if pending_chapter_count == 1 else "chapters"
        chapter_count_var.set(f"{pending_chapter_count} {chapter_label}")
        set_processing_state(False)
        show_output()
        output_text.configure(state="normal")
        output_text.delete("1.0", tk.END)
        output_text.configure(state="disabled")
        write_output(f"📘 Loaded: {os.path.basename(clean_path(file_path))}")
        if pending_duration_ms > 0:
            write_output(f"⏱️ Duration: {format_duration(pending_duration_ms)}")
        else:
            write_output("⏱️ Duration: Unknown (enter Manual Duration hours/minutes)")
        write_output(f"📖 Existing chapters: {pending_chapter_count}")
        write_output("\nSet a chapter interval and click Set Chapters.")
        update_progress(0)

    root.after(0, update_ui)


def on_set_chapters():
    if not pending_file or is_processing:
        return
    normalize_minutes_field()
    try:
        interval_minutes = int(minutes_var.get())
    except ValueError:
        messagebox.showerror("Invalid Interval", "Set chapters every value must be between 01 and 60 minutes.")
        return

    if not 1 <= interval_minutes <= 60:
        messagebox.showerror("Invalid Interval", "Set chapters every value must be between 01 and 60 minutes.")
        return

    normalize_manual_duration_fields()
    try:
        effective_duration_ms, using_manual_duration, manual_hours, manual_minutes = get_effective_duration_ms()
    except ValueError as exc:
        messagebox.showerror("Duration Required", str(exc))
        return

    set_processing_state(True, "⏳ Rebuilding chapter data...")
    show_output()
    output_text.configure(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.configure(state="disabled")
    write_output(f"📘 Source: {os.path.basename(clean_path(pending_file))}")
    write_output(f"📖 Existing chapters: {pending_chapter_count}")
    if using_manual_duration:
        write_output(f"⏱️ Using manual duration: {manual_hours}h {manual_minutes:02d}m")
    write_output(f"✂️ Splitting into {interval_minutes:02d}-minute chapters...")
    update_progress(20)

    def worker():
        try:
            root.after(0, lambda: update_progress(45))
            output_path, generated_count, detected_count = set_chapters(
                pending_file,
                effective_duration_ms,
                interval_minutes,
            )
        except Exception as exc:
            root.after(0, lambda err=str(exc): (
                write_output(f"⚠️ {err}"),
                update_progress(0),
                set_processing_state(False)
            ))
            return

        def finish():
            update_progress(100)
            write_output(f"✅ Done! → {os.path.basename(output_path)}")
            write_output(f"📂 Saved to: {os.path.dirname(output_path)}")
            write_output(f"📖 Generated chapters: {generated_count}")
            write_output(f"🔎 Output chapters detected: {detected_count}")
            if detected_count in (0, 1):
                write_output("⚠️ Warning: output contains only 1 or 0 chapters.")
            root.after(1500, lambda: update_progress(0))
            set_processing_state(False)

        root.after(0, finish)

    threading.Thread(target=worker, daemon=True).start()


def drop_event_handler(event):
    if is_processing:
        return

    try:
        raw = root.tk.call("set", "::tkdnd::_dropped_data")
    except Exception:
        raw = event.data

    raw_paths = parse_dropped_paths(raw)
    hide_output(clear=True)

    if len(raw_paths) != 1:
        show_output()
        write_output("⚠️ Drop exactly one .m4b file.")
        return

    raw_path = raw_paths[0]
    normalized = normalize_path(raw_path)
    if not os.path.isfile(normalized):
        show_output()
        write_output("⚠️ The dropped item is not a file.")
        return

    if os.path.splitext(raw_path)[1].lower() != ".m4b":
        show_output()
        write_output("⚠️ Only .m4b files are supported.")
        return

    set_processing_state(True, "🔍 Detecting chapter data...")
    show_output()
    write_output(f"📘 Reading metadata from {os.path.basename(clean_path(normalized))}...")
    update_progress(10)
    threading.Thread(target=lambda: probe_file(normalized), daemon=True).start()


if not check_ffmpeg():
    messagebox.showerror(
        "ffmpeg Not Found",
        "ffmpeg and ffprobe must be installed and on your PATH.\n\nInstall via: winget install ffmpeg"
    )


info_frame = ttk.LabelFrame(root, text=" File Info ", padding=(8, 4))
info_frame.pack(padx=10, pady=(10, 0), fill="x")
info_frame.columnconfigure(1, weight=1)

ttk.Label(info_frame, text="File:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
ttk.Label(info_frame, textvariable=file_name_var).grid(row=0, column=1, sticky="w", pady=2)
ttk.Label(info_frame, text="Duration:").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
ttk.Label(info_frame, textvariable=duration_var).grid(row=1, column=1, sticky="w", pady=2)
ttk.Label(info_frame, text="Chapters:").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=2)
ttk.Label(info_frame, textvariable=chapter_count_var).grid(row=2, column=1, sticky="w", pady=2)


controls_frame = ttk.LabelFrame(root, text=" Chapter Split ", padding=(8, 8))
controls_frame.pack(padx=10, pady=(10, 0), fill="x")

validate_minutes_cmd = root.register(validate_minutes)
validate_manual_hours_cmd = root.register(validate_manual_hours)
validate_manual_minutes_cmd = root.register(validate_manual_minutes)

interval_row = ttk.Frame(controls_frame)
interval_row.pack(fill="x")

manual_row = ttk.Frame(controls_frame)
manual_row.pack(fill="x", pady=(8, 0))

ttk.Label(interval_row, text="Set chapters every").pack(side="left")
minutes_entry = ttk.Entry(
    interval_row,
    textvariable=minutes_var,
    width=4,
    justify="center",
    validate="key",
    validatecommand=(validate_minutes_cmd, "%P"),
)
minutes_entry.pack(side="left", padx=6)
minutes_entry.bind("<FocusOut>", normalize_minutes_field)
ttk.Label(interval_row, text="minutes").pack(side="left")

set_button = ttk.Button(controls_frame, text="Set Chapters", command=on_set_chapters, state="disabled")
set_button.pack(in_=interval_row, side="right")

ttk.Label(manual_row, text="Manual Duration (if unknown):").pack(side="left")
manual_hours_entry = ttk.Entry(
    manual_row,
    textvariable=manual_duration_hours_var,
    width=5,
    justify="center",
    validate="key",
    validatecommand=(validate_manual_hours_cmd, "%P"),
)
manual_hours_entry.pack(side="left", padx=(6, 4))
manual_hours_entry.bind("<FocusOut>", normalize_manual_duration_fields)
ttk.Label(manual_row, text="hours").pack(side="left")

manual_minutes_entry = ttk.Entry(
    manual_row,
    textvariable=manual_duration_minutes_var,
    width=4,
    justify="center",
    validate="key",
    validatecommand=(validate_manual_minutes_cmd, "%P"),
)
manual_minutes_entry.pack(side="left", padx=(8, 4))
manual_minutes_entry.bind("<FocusOut>", normalize_manual_duration_fields)
ttk.Label(manual_row, text="minutes").pack(side="left")


DRAG_TEXT = (
    "📚 Drag and drop one .m4b file here\n"
    "Folders are not supported.\n\n"
    "The app will detect existing chapter count, then rewrite chapters into fixed minute intervals."
)

drag_label = ttk.Label(
    root,
    text=DRAG_TEXT if dnd_available else "Drag-and-drop not available.\nInstall tkinterdnd2 for full functionality.",
    anchor="center",
    relief="solid",
    padding=10,
    font=("Segoe UI Emoji", 12),
    justify="center",
)
drag_label.pack(padx=10, pady=10, fill="both", expand=True, ipady=18)


output_frame = ttk.Frame(root)
progress_bar = ttk.Progressbar(output_frame, orient="horizontal", mode="determinate")
progress_bar.pack(fill="x", padx=10, pady=(0, 5))
progress_bar["maximum"] = 100

output_header = ttk.Frame(output_frame)
output_header.pack(fill="x")
ttk.Label(output_header, text="📋 Chapter Log", anchor="w").pack(side="left", padx=(5, 0), pady=2)
ttk.Button(output_header, text="❌", width=3, command=lambda: hide_output(clear=True)).pack(side="right", padx=5, pady=2)

output_text_frame = ttk.Frame(output_frame)
output_text_frame.pack(fill="both", expand=True)
scrollbar = ttk.Scrollbar(output_text_frame)
scrollbar.pack(side="right", fill="y")
output_text = tk.Text(output_text_frame, wrap="word", height=10, yscrollcommand=scrollbar.set, state="disabled")
output_text.pack(side="left", fill="both", expand=True)
scrollbar.config(command=output_text.yview)
output_frame.pack_forget()


if dnd_available:
    drag_label.drop_target_register(tkdnd.DND_FILES)
    drag_label.dnd_bind("<<Drop>>", drop_event_handler)


if __name__ == "__main__":
    try:
        root.mainloop()
    except Exception as exc:
        import traceback
        trace = traceback.format_exc()
        with open("m4b-chapter-editor-error.log", "w", encoding="utf-8") as handle:
            handle.write(trace)
        messagebox.showerror("Startup Crash", f"{type(exc).__name__}: {exc}")