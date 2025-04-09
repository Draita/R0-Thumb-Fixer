import os
import io
import sys
import threading
import subprocess
import platform
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from PIL import Image, UnidentifiedImageError
import tkinter as tk
from tkinter import filedialog, ttk
import tkinter.messagebox as messagebox
import logging

# --- Configuration ---
MAX_ARTWORK_SIZE = (500, 500)
JPEG_QUALITY = 85
# --- End Configuration ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def is_artwork_oversized(artwork_data):
    try:
        img = Image.open(io.BytesIO(artwork_data))
        return img.width > MAX_ARTWORK_SIZE[0] or img.height > MAX_ARTWORK_SIZE[1]
    except UnidentifiedImageError:
        log_message("Warning: Could not identify image format for size check.", logging.WARNING)
        print_to_gui("> Warning: Could not identify image format for size check.")
        return False
    except Exception as e:
        log_message(f"Error checking artwork size: {e}", logging.ERROR)
        print_to_gui(f"> Error checking artwork size: {e}")
        return False

def optimize_artwork_for_yp_r0(artwork_data, temp_jpeg_path):
    try:
        img = Image.open(io.BytesIO(artwork_data))
        if img.mode != 'RGB':
            img = img.convert("RGB")

        original_size = img.size
        img.thumbnail(MAX_ARTWORK_SIZE, Image.Resampling.LANCZOS)
        new_size = img.size
        if new_size != original_size:
            log_message(f"Resized artwork from {original_size} to {new_size}", logging.INFO)
            print_to_gui(f"> Resized artwork from {original_size} to {new_size}")

        img.save(temp_jpeg_path,
                format="JPEG",
                quality=JPEG_QUALITY,
                optimize=False,
                progressive=False,
                subsampling=0)
        log_message(f"Saved optimized artwork to: {temp_jpeg_path}", logging.INFO)
        print_to_gui(f"> Saved optimized artwork to: {temp_jpeg_path}")
        return temp_jpeg_path
    except Exception as e:
        log_message(f"Error optimizing artwork: {e}", logging.ERROR)
        print_to_gui(f"> Error optimizing artwork: {e}")
        return None

def embed_jpeg_in_mp3_mutagen(mp3_file, jpeg_path):
    try:
        with open(jpeg_path, 'rb') as f:
            image_data = f.read()

        audio = MP3(mp3_file, ID3=ID3)
        keys_to_delete = [key for key in audio.tags if key.startswith('APIC:')]
        for key in keys_to_delete:
            del audio.tags[key]

        audio.tags.add(
            APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=image_data
            )
        )
        audio.save()
        log_message("Replaced album art with optimized version.", logging.INFO)
        print_to_gui("> Replaced album art with optimized version.")
        return True
    except Exception as e:
        log_message(f"Error embedding JPEG: {e}", logging.ERROR)
        print_to_gui(f"> Error embedding JPEG: {e}")
        return False

def process_mp3_file(mp3_path):
    artwork_changed = False
    try:
        audio = MP3(mp3_path, ID3=ID3)
    except ID3NoHeaderError:
        log_message(f"No ID3 tags found. Skipping: {mp3_path}", logging.WARNING)
        print_to_gui(f"> No ID3 tags found. Skipping: {mp3_path}")
        return artwork_changed
    except Exception as e:
        log_message(f"Error reading MP3 tags: {e}", logging.ERROR)
        print_to_gui(f"> Error reading MP3 tags: {e}")
        return artwork_changed

    found_art_tag = None
    for key in audio.tags:
        if key.startswith('APIC:'):
            found_art_tag = audio.tags[key]
            break

    if found_art_tag:
        if is_artwork_oversized(found_art_tag.data):
            log_message("Artwork exceeds maximum dimensions. Optimizing...", logging.INFO)
            print_to_gui("> Artwork exceeds maximum dimensions. Optimizing...")
            base_name = os.path.splitext(os.path.basename(mp3_path))[0]
            temp_jpeg_path = os.path.join(os.path.dirname(mp3_path), f"{base_name}_temp_opt.jpg")
            optimized_path = optimize_artwork_for_yp_r0(found_art_tag.data, temp_jpeg_path)
            if optimized_path:
                if embed_jpeg_in_mp3_mutagen(mp3_path, optimized_path):
                    artwork_changed = True
                    try:
                        os.remove(optimized_path)
                        log_message(f"Removed temporary file: {mp3_path}", logging.INFO)
                        print_to_gui("> Removed temporary file")
                    except OSError:
                        log_message(f"Warning: Could not remove temporary file: {mp3_path}", logging.WARNING)
                        print_to_gui(f"> Warning: Could not remove temporary file: {mp3_path}")
                else:
                    log_message("Failed to embed optimized artwork.", logging.ERROR)
                    print_to_gui("> Failed to embed optimized artwork.")
            else:
                log_message("Artwork optimization failed.", logging.ERROR)
                print_to_gui("> Artwork optimization failed.")
        else:
            log_message("Artwork dimensions are within limits. Skipping.", logging.INFO)

    else:
        log_message(f"No embedded album art found. Skipping: {mp3_path}", logging.INFO)
        print_to_gui(f"> No embedded album art found. Skipping: {mp3_path}")
    return artwork_changed

def process_all_mp3s(directory_path, all_files, processed_files):
    for root, _, files in os.walk(directory_path):
        for filename in files:
            if filename.lower().endswith(".mp3"):
                mp3_file_path = os.path.join(root, filename)
                all_files.append(mp3_file_path)
                artwork_changed = process_mp3_file(mp3_file_path)
                processed_files.append((mp3_file_path, artwork_changed))
            else:
                log_message(f"Skipping non-MP3 file: {filename} in {root}", logging.DEBUG)

def process_directory(directory_path):
    all_files = []
    processed_files = []
    log_message(f"Starting recursive processing in: {directory_path}", logging.INFO)
    print_to_gui(f"> Starting recursive processing in: {directory_path}")
    process_all_mp3s(directory_path, all_files, processed_files)

    total_files = len(all_files)
    log_message(f"Processing {total_files} MP3 files.", logging.INFO)

    for i, (mp3_file_path, artwork_changed) in enumerate(processed_files):
        if artwork_changed:
            log_message(f"Processing: {mp3_file_path}", logging.INFO)
            print_to_gui(f"> Processing: {mp3_file_path}")
            log_message(f"Artwork Optimized: {mp3_file_path}", logging.INFO)
        update_progress((i + 1) / total_files * 100)

    log_message(f"Finished recursive processing in: {directory_path}", logging.INFO)
    print_to_gui(f"> Finished recursive processing in: {directory_path}")

def process_files_wrapper(directory):
    global stop_processing
    stop_processing = False
    try:
        process_directory(directory)
        if stop_processing:
            messagebox.showinfo("Info", "Processing stopped by user.")
            log_message("Processing stopped by user.", logging.INFO)
        else:
            messagebox.showinfo("Info", "Finished processing all MP3 files.")
            log_message("Finished processing all MP3 files.", logging.INFO)
    except Exception as e:
        log_message(f"An error occurred: {e}", logging.ERROR)
        print_to_gui(f"> An error occurred: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        enable_buttons()
        update_progress(0)

def browse_directory():
    directory = filedialog.askdirectory()
    if directory:
        directory_entry.delete(0, tk.END)
        directory_entry.insert(0, directory)

def open_file_explorer(path):
    try:
        path = os.path.normpath(path)
        path = f'"{path}"'
        subprocess.Popen(f'explorer {path}')
    except FileNotFoundError:
        messagebox.showerror("Error", "File Explorer not found.")
    except Exception as e:
        messagebox.showerror("Error", f"Error opening File Explorer: {e}")

def start_processing():
    global stop_processing
    stop_processing = False
    directory = directory_entry.get()
    if not os.path.isdir(directory):
        messagebox.showerror("Error", "Invalid directory selected.")
        return

    log_message(f"Starting processing in directory: {directory}", logging.INFO)
    disable_buttons()
    threading.Thread(target=process_files_wrapper, args=(directory,), daemon=True).start()

def stop_processing_callback():
    global stop_processing
    stop_processing = True
    log_message("Stopping processing...", logging.INFO)
    print_to_gui("Stopping processing...")

def update_progress(value):
    progress_bar['value'] = value
    root.update_idletasks()

def print_to_gui(text):
    output_text.insert(tk.END, "> " + text + "\n")
    output_text.see(tk.END)
    root.update_idletasks()

def log_message(message, level=logging.INFO):
    logging.log(level, message)

def disable_buttons():
    browse_button['state'] = tk.DISABLED
    start_button['state'] = tk.DISABLED
    stop_button['state'] = tk.NORMAL

def enable_buttons():
    browse_button['state'] = tk.NORMAL
    start_button['state'] = tk.NORMAL
    stop_button['state'] = tk.DISABLED

def check_dependencies():
    try:
        import PIL
        import mutagen
    except ImportError as e:
        messagebox.showerror("Error", f"Missing required library - {e.name}\nPlease install them using: pip install Pillow mutagen")
        root.destroy()
        sys.exit(1)

# --- GUI Setup ---
root = tk.Tk()
root.title("YP-R0 MP3 Thumbnail Optimizer")
root.geometry("800x600")

# Directory Selection
directory_label = tk.Label(root, text="Directory:")
directory_label.pack()

directory_entry = tk.Entry(root, width=70)
directory_entry.pack()

browse_button = tk.Button(root, text="Browse", command=browse_directory)
browse_button.pack()

# Progress Bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=500, mode="determinate")
progress_bar.pack(pady=10)

# Output Text Area
output_text = tk.Text(root, height=15, width=90)
output_text.pack(pady=10)

# Start and Stop Buttons
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

start_button = tk.Button(button_frame, text="Start Processing", command=start_processing)
start_button.pack(side=tk.LEFT, padx=10)

stop_button = tk.Button(button_frame, text="Stop Processing", command=stop_processing_callback, state=tk.DISABLED)
stop_button.pack(side=tk.LEFT, padx=10)

# Scrollbar for Text Area
scrollbar = tk.Scrollbar(root, command=output_text.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
output_text['yscrollcommand'] = scrollbar.set

# Global flag to stop processing
stop_processing = False

check_dependencies()

root.mainloop()