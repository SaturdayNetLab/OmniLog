# 🦁 Omnilog - The Ultimate Log Analyzer

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.x-yellow)
![License](https://img.shields.io/badge/license-MIT-green)

**Omnilog** is a modern, fast, and feature-rich log analysis tool built with Python and CustomTkinter. Designed for Sysadmins, DevOps, and Developers who need to dig through massive log files efficiently.

It features a beautiful dark mode, instant search with regex support, live monitoring, and zero-ghosting synchronized line numbers.

![Screenshot](screenshots/main_preview.png)
*(Note: Add a screenshot of your tool here and name it main_preview.png inside a screenshots folder)*

## ✨ Key Features

* **🎨 Modern UI:** Clean dark theme based on `CustomTkinter`.
* **drag & Drop:** Simply drag log files into the window to open them.
* **📋 Clipboard Integration:** Analyze text directly from your clipboard with one click.
* **🔍 Powerful Search:**
    * Full Regex support (toggleable).
    * Keyboard navigation (`<` and `>`) through matches.
    * Instant hit counting.
* **⚡ Smart Filtering:**
    * Filter by Log Level (`ERROR`, `WARN`, `INFO`, `DEBUG`).
    * **Exclude Mode:** Hide lines containing specific noise (e.g., "Heartbeat").
    * **Sync:** Line numbers hide automatically to match the filtered view.
* **🔴 Live Watch (Tail -f):** Monitor active log files in real-time as they grow.
* **🛠 Pro Tools:**
    * **Context Menu:** Right-click to search errors on Google immediately.
    * **Marking:** Highlight lines in Red, Blue, or Yellow.
    * **Notes:** Add custom notes to specific lines and view them in a summary.
    * **Stats:** Visual bar chart of log level distribution.
* **📂 Export:** Save your filtered results or annotated analysis as `.txt` or `.json`.

## 🚀 Installation

### Option 1: Download EXE (Recommended)
Go to the [Releases](../../releases) page and download the latest `omnilog.exe`. No Python installation required.

### Option 2: Run from Source
If you want to modify the code or run it via Python:

1.  Clone the repository:
    ```bash
    git clone [https://github.com/YOUR_USERNAME/omnilog.git](https://github.com/YOUR_USERNAME/omnilog.git)
    cd omnilog
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Run the application:
    ```bash
    python omnilog.py
    ```

## 🖱️ Context Menu Integration ("Open with...")

You can add Omnilog to your Windows right-click menu to open log files instantly.

1.  Build the EXE or use the Python script.
2.  Open `install_context.py` in a text editor.
3.  Edit the `exe_path` variable to point to your `omnilog.exe`.
4.  Run the script as Administrator.

## 📦 How to Build (EXE)

To compile Omnilog into a standalone executable:

1.  Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```

2.  Run the build command:
    ```bash
    py -m PyInstaller --noconsole --onefile --collect-all customtkinter --collect-all tkinterdnd2 omnilog.py
    ```

3.  (Optional) Add an icon:
    ```bash
    py -m PyInstaller --noconsole --onefile --icon="app.ico" --collect-all customtkinter --collect-all tkinterdnd2 omnilog.py
    ```

The output file will be in the `dist/` folder.

## 🛠 Dependencies

* `customtkinter` (UI Framework)
* `tkinterdnd2` (Drag & Drop support)
* `chardet` (Encoding detection)
* `matplotlib` (Statistics charts)

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## 📝 License

[MIT](https://choosealicense.com/licenses/mit/)
