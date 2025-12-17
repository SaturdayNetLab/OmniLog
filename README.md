# 🦁 Omnilog - The Ultimate Log Analyzer

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.x-yellow)
![License](https://img.shields.io/badge/license-MIT-green)

**Omnilog** is a modern, high-performance log analysis tool designed for System Administrators, DevOps, and Developers. It simplifies debugging by providing a clean, dark-themed interface with powerful search, filtering, and live-monitoring capabilities.

![Screenshot](screenshots/main_preview.png)

## ✨ Key Features

* **⚡ Zero-Ghosting Line Numbers:** Custom-built synchronization engine ensures line numbers never overlap or desync, even during heavy filtering.
* **🔍 Advanced Search:**
    * **Regex Support:** Toggleable Regex search with useful presets (IPs, Emails, Dates, etc.).
    * **Navigation:** Cycle through matches instantly.
* **🛡️ Smart Filtering:**
    * Filter by Log Level (`ERROR`, `WARN`, `INFO`, `DEBUG`).
    * **Exclude Mode:** Hide noise (e.g., "Heartbeat") instantly.
    * **Sync:** Line numbers hide automatically to match the filtered view.
* **🔴 Live Watch (Tail -f):** Monitor active log files in real-time. New lines appear automatically.
* **🛠 Pro Toolset:**
    * **Context Search:** Right-click any text to search it on Google immediately.
    * **Marking & Notes:** Highlight lines (Red/Blue/Yellow) and attach persistent notes.
    * **Zoom Control:** Adjust font size with `Ctrl + Scroll` or UI buttons.
    * **Statistics:** Visualize log level distribution with built-in charts.
* **📂 Export:** Save filtered results or annotated analysis as `.txt` or `.json`.

## 📥 Download & Installation

### Option 1: Standalone EXE (Recommended for Users)
You don't need Python installed. Just download the latest executable:

1.  Go to the **[Releases](../../releases)** page on the right.
2.  Download `omnilog.exe`.
3.  Run it! 

*(Note: Since this is a self-signed tool, Windows Defender might warn you on the first run. Click "Run anyway".)*

### Option 2: Run from Source (For Developers)
If you want to modify the code or contribute:

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

## 🖱️ Add to Windows Context Menu

Want to right-click a log file and select **"Open with Omnilog"**?

1.  Download the EXE (or have the Python source ready).
2.  Open `install_context.py` in a text editor.
3.  Update the `exe_path` variable to point to your `omnilog.exe` location.
4.  Run the script as Administrator once.

## 📦 Building the EXE

To compile Omnilog yourself using PyInstaller:

```powershell
py -m PyInstaller --noconsole --onefile --collect-all customtkinter --collect-all tkinterdnd2 omnilog.py
