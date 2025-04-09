# YP-R0 MP3 Thumbnail Optimizer

## Description

The YP-R0 MP3 Thumbnail Optimizer is a Python-based GUI application designed to process MP3 files and ensure their embedded album art (thumbnails) are compatible with the YP-R0 MP3 player, which has specific requirements for artwork dimensions. The program recursively scans a directory and its subdirectories, resizes oversized album art to fit within the YP-R0's limits (500x500 pixels), and re-embeds the optimized artwork into the MP3 files.

## Features

*   **Recursive Directory Processing:** Scans a specified directory and all its subdirectories for MP3 files.
*   **Automatic Artwork Optimization:** Automatically identifies and resizes oversized embedded album art.
*   **YP-R0 Compatibility:** Ensures artwork is within the YP-R0's maximum dimensions (500x500 pixels) for optimal display.
*   **GUI Interface:** Provides a user-friendly graphical interface for easy operation.
*   **Progress Bar:** Displays a progress bar to track the processing status.
*   **Logging:** Logs processing activity and any errors encountered to the console and a GUI text area.
*   **Single Executable (via PyInstaller):** Can be compiled into a single `.exe` file for easy distribution and execution on Windows.

## Requirements

*   **Python 3:** Python 3.6 or higher is required.
*   **Libraries:** The following Python libraries are required and can be installed using `pip`:
    *   `Pillow` (PIL): For image processing.
    *   `mutagen`: For reading and writing MP3 metadata (ID3 tags).
    *   `tkinter`: For the graphical user interface (usually included with Python installations).

## Installation

1.  **Install Python 3:** If you don't have Python 3 installed, download and install it from [https://www.python.org/](https://www.python.org/).

2.  **Install Required Libraries:** Open a command prompt or terminal and run:

    ```bash
    pip install Pillow mutagen
    ```

## Usage

1.  **Run the Script:** Execute the Python script (`your_script_name.py`) or the compiled executable (`your_script_name.exe`).

2.  **Select Directory:** Use the "Browse" button to select the directory containing the MP3 files you want to process.

3.  **Start Processing:** Click the "Start Processing" button. The program will begin scanning the directory and optimizing the artwork in the MP3 files. A progress bar will indicate the processing status.

4.  **Stop Processing (Optional):** If you need to interrupt the processing, click the "Stop Processing" button.

5.  **Monitor Progress:** The output text area in the GUI will display the progress and any errors encountered.

## Compilation (Creating an Executable)

To create a standalone executable for Windows, you can use PyInstaller:

1.  **Install PyInstaller:**

    ```bash
    pip install pyinstaller
    ```

2.  **Run PyInstaller:**

    ```bash
    pyinstaller --onefile --noconsole your_script_name.py
    ```

    *   `--onefile`: Creates a single executable file.
    *   `--noconsole`: Prevents a console window from appearing when the executable is run (recommended for GUI applications).

3.  **Find the Executable:** The resulting executable (`your_script_name.exe`) will be located in the `dist` folder.

**Linux Compilation**

1. Intall necessary dependencies and libraries
2. Use command to create executable `pyinstaller --onefile --noconsole your_script_name.py`

## Configuration

The following configuration options are available at the top of the script:

*   `MAX_ARTWORK_SIZE`:  A tuple specifying the maximum width and height (in pixels) for the album art (default: `(500, 500)`).
*   `JPEG_QUALITY`: An integer specifying the quality level for the saved temporary JPEG files (default: `85`).

## Logging

The program provides logging to both the console and a GUI text area:

*   **Console Logging:** Detailed log messages are printed to the console, providing information about the processing steps, any warnings, and errors.
*   **GUI Text Area:** A summary of the processing activity is displayed in the GUI text area, with a ">" prefix for each line.

## Notes

*   The program creates temporary JPEG files during the optimization process. These files are typically deleted automatically, but in rare cases, you might need to manually remove them from the MP3 file directories.
*   The program modifies the ID3 tags of the MP3 files in place. It is always a good idea to back up your music library before running any program that modifies metadata.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
