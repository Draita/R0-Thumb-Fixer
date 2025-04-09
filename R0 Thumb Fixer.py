import os
import io
import sys
import threading
import subprocess  # Import for opening file explorer
import platform  # Import for OS detection
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from PIL import Image, UnidentifiedImageError
import tkinter as tk
from tkinter import filedialog, ttk
import tkinter.messagebox as messagebox
import logging  # Import for logging

# --- Configuration ---
# Set the desired maximum size for the artwork (width, height) for YP-R0 compatibility
MAX_ARTWORK_SIZE = (500, 500)
# Set the quality for the saved temporary JPEG
JPEG_QUALITY = 85
# --- End Configuration ---

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def is_artwork_oversized(artwork_data):
    """Checks if the artwork data represents an image larger than MAX_ARTWORK_SIZE."""
    try:
        img = Image.open(io.BytesIO(artwork_data))
        return img.width > MAX_ARTWORK_SIZE[0] or img.height > MAX_ARTWORK_SIZE[1]
    except UnidentifiedImageError:
        log_message("Warning: Could not identify image format for size check.", logging.WARNING)
        print_to_gui("Warning: Could not identify image format for size check.")
        return False
    except Exception as e:
        log_message(f"Error checking artwork size: {e}", logging.ERROR)
        print_to_gui(f"Error checking artwork size: {e}")
        return False

def optimize_artwork_for_yp_r0(artwork_data, temp_jpeg_path):
    """Resizes and saves artwork as a compatible JPEG."""
    try:
        img = Image.open(io.BytesIO(artwork_data))
        if img.mode != 'RGB':
            img = img.convert("RGB")

        original_size = img.size
        img.thumbnail(MAX_ARTWORK_SIZE, Image.Resampling.LANCZOS)
        new_size = img.size
        if new_size != original_size:
            log_message(f"Resized artwork from {original_size} to {new_size}", logging.INFO)
            print_to_gui(f"  Resized artwork from {original_size} to {new_size}")

        img.save(temp_jpeg_path,
                format="JPEG",
                quality=JPEG_QUALITY,
                optimize=False,
                progressive=False,
                subsampling=0)
        log_message(f"Saved optimized artwork to: {temp_jpeg_path}", logging.INFO)
        print_to_gui(f"  Saved optimized artwork to: {temp_jpeg_path}")
        return temp_jpeg_path
    except Exception as e:
        log_message(f"Error optimizing artwork: {e}", logging.ERROR)
        print_to_gui(f"Error optimizing artwork: {e}")
        return None

def embed_jpeg_in_mp3_mutagen(mp3_file, jpeg_path):
    """Replaces existing APIC tag with the JPEG at the given path."""
    try:
        with open(jpeg_path, 'rb') as f:
            image_data = f.read()

        audio = MP3(mp3_file, ID3=ID3)

        # Remove all existing APIC frames
        keys_to_delete = [key for key in audio.tags if key.startswith('APIC:')]
        for key in keys_to_delete:
            del audio.tags[key]

        # Add the new APIC frame
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
        print_to_gui("  Replaced album art with optimized version.")
        return True
    except Exception as e:
        log_message(f"Error embedding JPEG: {e}", logging.ERROR)
        print_to_gui(f"Error embedding JPEG: {e}")
        return False

def process_mp3_file(mp3_path):
    """Processes a single MP3 file for YP-R0 compatible thumbnail."""
    artwork_changed = False # Add this flag

    try:
        audio = MP3(mp3_path, ID3=ID3)
    except ID3NoHeaderError:
        log_message(f"No ID3 tags found. Skipping: {mp3_path}", logging.WARNING) #Include filename
        print_to_gui(f"No ID3 tags found. Skipping: {mp3_path}") #GUI output added
        return artwork_changed  # Return False
    except Exception as e:
        log_message(f"Error reading MP3 tags: {e}", logging.ERROR)
        print_to_gui(f" Error reading MP3 tags: {e}")
        return artwork_changed  # Return False

    found_art_tag = None
    for key in audio.tags:
        if key.startswith('APIC:'):
            found_art_tag = audio.tags[key]
            break

    if found_art_tag:
        if is_artwork_oversized(found_art_tag.data):
            
            log_message("Artwork exceeds maximum dimensions. Optimizing...", logging.INFO)
            print_to_gui("  Artwork exceeds maximum dimensions. Optimizing...")
            base_name = os.path.splitext(os.path.basename(mp3_path))[0]
            temp_jpeg_path = os.path.join(os.path.dirname(mp3_path), f"{base_name}_temp_opt.jpg")
            optimized_path = optimize_artwork_for_yp_r0(found_art_tag.data, temp_jpeg_path)
            if optimized_path:
                if embed_jpeg_in_mp3_mutagen(mp3_path, optimized_path):
                    artwork_changed = True # artwork was optimized
                    try:
                        os.remove(optimized_path)
                        log_message(f"Removed temporary file: {optimized_path}", logging.INFO)
                    except OSError:
                        log_message(f"Warning: Could not remove temporary file: {optimized_path}", logging.WARNING)
                        print_to_gui(f"Warning: Could not remove temporary file: {optimized_path}")
                else:
                    log_message("Failed to embed optimized artwork.", logging.ERROR)
                    print_to_gui("  Failed to embed optimized artwork.")
            else:
                log_message("Artwork optimization failed.", logging.ERROR)
                print_to_gui("  Artwork optimization failed.")
        else:
            log_message("Artwork dimensions are within limits. Skipping.", logging.INFO)
        
    else:
        log_message(f"No embedded album art found. Skipping: {mp3_path}", logging.INFO) # added path
        print_to_gui(f"  No embedded album art found. Skipping: {mp3_path}") #GUI UPDATED
    return artwork_changed

def process_all_mp3s(directory_path, all_files, processed_files): # changed process all mp3s
    """Recursively processes all MP3 files in a directory and its subdirectories."""
    for root, _, files in os.walk(directory_path):  # Use os.walk
        for filename in files:
            if filename.lower().endswith(".mp3"):
                mp3_file_path = os.path.join(root, filename)
                all_files.append(mp3_file_path)
                artwork_changed = process_mp3_file(mp3_file_path)  # Capture the boolean
                processed_files.append((mp3_file_path, artwork_changed))
            else:
                log_message(f"Skipping non-MP3 file: {filename} in {root}", logging.DEBUG)
                #print_to_gui(f"Skipping non-MP3 file: {filename} in {root}")

def process_directory(directory_path):
    all_files = []
    processed_files = []
    log_message(f"Starting recursive processing in: {directory_path}", logging.INFO)
    print_to_gui(f"Starting recursive processing in: {directory_path}")
    process_all_mp3s(directory_path, all_files, processed_files)

    total_files = len(all_files)
    log_message(f"Processing {total_files} MP3 files.", logging.INFO)

    for i, (mp3_file_path, artwork_changed) in enumerate(processed_files): # process files
        if artwork_changed: # Log only if it has changed
            log_message(f"Processing: {mp3_file_path}", logging.INFO)
            print_to_gui(f"\nProcessing: {mp3_file_path}") # Only print to GUI *if* changed
            log_message(f"Artwork Optimized: {mp3_file_path}", logging.INFO) # logging if it's been changed
        update_progress((i + 1) / total_files * 100) # update progress bar

    log_message(f"Finished recursive processing in: {directory_path}", logging.INFO)
    print_to_gui(f"Finished recursive processing in: {directory_path}")

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
        print_to_gui(f"An error occurred: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        enable_buttons()
        update_progress(0)

def browse_directory():
    """Opens a directory selection dialog and sets the selected path to the entry field."""
    directory = filedialog.askdirectory()
    if directory:
        directory_entry.delete(0, tk.END)
        directory_entry.insert(0, directory)

def open_file_explorer(path):
    """Opens Windows File Explorer at the given path."""
    try:
        # Quote the path in case it contains spaces
        path = os.path.normpath(path) # Standardize path (fixes issues with mixed slashes)
        path = f'"{path}"' # Quote the path
        subprocess.Popen(f'explorer {path}')  # Modified to use f-string for robustness
    except FileNotFoundError:
        messagebox.showerror("Error", "File Explorer not found.")
    except Exception as e:
        messagebox.showerror("Error", f"Error opening File Explorer: {e}")

def start_processing():
    """Starts the processing in a separate thread."""
    global stop_processing
    stop_processing = False
    directory = directory_entry.get()
    if not os.path.isdir(directory):
        messagebox.showerror("Error", "Invalid directory selected.")
        return

    log_message(f"Starting processing in directory: {directory}", logging.INFO) # Logging the selected directory
    disable_buttons()
    threading.Thread(target=process_files_wrapper, args=(directory,), daemon=True).start()

def stop_processing_callback():
    """Stops the processing."""
    global stop_processing
    stop_processing = True
    log_message("Stopping processing...", logging.INFO)
    print_to_gui("Stopping processing...")

def update_progress(value):
    """Updates the progress bar value."""
    progress_bar['value'] = value
    root.update_idletasks()

def print_to_gui(text):
    """Prints text to the text area in the GUI."""
    output_text.insert(tk.END, "> " + text + "\n")  # Added > prefix
    output_text.see(tk.END)  # Scroll to the end
    root.update_idletasks()

def log_message(message, level=logging.INFO):
    """Logs a message to the console."""
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
root.geometry("800x600") # Increased size

# Directory Selection
directory_label = tk.Label(root, text="Directory:")
directory_label.pack()

directory_entry = tk.Entry(root, width=70) # Increased width
directory_entry.pack()

browse_button = tk.Button(root, text="Browse", command=browse_directory)
browse_button.pack()

# Progress Bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=500, mode="determinate") # Increased length
progress_bar.pack(pady=10)

# Output Text Area
output_text = tk.Text(root, height=15, width=90) # Increased size
output_text.pack(pady=10)

# Start and Stop Buttons
button_frame = tk.Frame(root) # Frame to group buttons
button_frame.pack(pady=10)

start_button = tk.Button(button_frame, text="Start Processing", command=start_processing)
start_button.pack(side=tk.LEFT, padx=10)

stop_button = tk.Button(button_frame, text="Stop Processing", command=stop_processing_callback, state=tk.DISABLED)
stop_button.pack(side=tk.LEFT, padx=10)

# Global flag to stop processing
stop_processing = False

check_dependencies()

root.mainloop()