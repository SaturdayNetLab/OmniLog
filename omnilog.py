import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, Menu, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import os
import sys
import re
import json
import chardet
import time
import webbrowser
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# --- Optimized Line Numbers (Synced Text Widget) ---
class LineNumberWidget(tk.Text):
    """
    Renders line numbers using a secondary Text widget.
    Guarantees perfect synchronization with the main text area.
    """
    def __init__(self, master, target_widget, **kwargs):
        super().__init__(master, width=6, padx=4, highlightthickness=0, takefocus=0, bd=0,
                         background="#1e1e1e", foreground="#666666", state="disabled", **kwargs)
        self.target_widget = target_widget
        self.configure(font=("Consolas", 13)) 
        
        # Tag configuration for hiding lines (Must match main text behavior)
        self.tag_config("hidden", elide=True)

        # Disable mouse interaction
        self.bind('<Button-1>', lambda e: "break")
        self.bind('<B1-Motion>', lambda e: "break")
        self.bind('<Double-Button-1>', lambda e: "break")
        self.bind('<Control-Button-1>', lambda e: "break")

    def populate(self, line_count):
        """Re-populates the line numbers from scratch (1 to N)."""
        self.configure(state="normal")
        self.delete("1.0", "end")
        line_content = "\n".join(str(i) for i in range(1, line_count + 1))
        self.insert("1.0", line_content)
        self.configure(state="disabled")
        self.sync_scroll()

    def sync_scroll(self, *args):
        """Syncs the y-view with the target widget."""
        yview = self.target_widget.yview()
        self.yview_moveto(yview[0])

# --- Data Management ---
class LogMeta:
    def __init__(self):
        self.annotations = {} 

    def add_annotation(self, line_index, color=None, note=None):
        line_key = str(line_index)
        if line_key not in self.annotations: self.annotations[line_key] = {}
        if color: self.annotations[line_key]['color'] = color
        if note: self.annotations[line_key]['note'] = note
    
    def get_annotation(self, line_index):
        return self.annotations.get(str(line_index), {})
    
    def get_all_notes(self):
        return {k: v for k, v in self.annotations.items() if 'note' in v}

# --- Main Log Tab ---
class LogTab(ctk.CTkFrame):
    def __init__(self, master, file_path=None, content=None, title="Untitled", **kwargs):
        super().__init__(master, **kwargs)
        self.file_path = file_path
        self.file_name = title if not file_path else os.path.basename(file_path)
        self.content_source = content 
        self.meta_data = LogMeta()
        
        # State variables
        self.search_matches = []
        self.current_match_index = -1
        self.font_size = 13
        self.is_watching = False 
        self.last_file_size = 0
        self.total_lines = 0
        
        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Text Area
        self.text_area = ctk.CTkTextbox(self, font=("Consolas", self.font_size), activate_scrollbars=True, undo=True, wrap="none")
        
        # 2. Line Numbers
        self.line_numbers = LineNumberWidget(self, self.text_area._textbox)
        self.line_numbers.grid(row=0, column=0, sticky="ns")
        
        # 3. Place Text Area
        self.text_area.grid(row=0, column=1, sticky="nsew", padx=(0, 5), pady=5)
        self.text_area.configure(state="disabled", fg_color="#2b2b2b")

        # 4. Tags & UI Setup
        self._configure_tags()
        self.status_bar = ctk.CTkFrame(self, height=30, fg_color="transparent")
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 5))
        self._setup_status_bar()
        self._setup_proxy_events()
        self.create_context_menu()
        
        # 5. Load Content
        if self.file_path: 
            try: self.last_file_size = os.path.getsize(self.file_path)
            except: pass
            self.start_loading_file()
        elif self.content_source: 
            self._update_text_area(self.content_source, "Clipboard")

    def _setup_status_bar(self):
        self.lbl_status = ctk.CTkLabel(self.status_bar, text="Loading...", text_color="orange", font=("Arial", 11))
        self.lbl_status.pack(side="left")
        self.lbl_note_display = ctk.CTkLabel(self.status_bar, text="", text_color="#aaaaaa", font=("Arial", 11, "italic"))
        self.lbl_note_display.pack(side="left", padx=20)
        self.lbl_cursor = ctk.CTkLabel(self.status_bar, text="Ln 1, Col 1", text_color="gray", font=("Arial", 11))
        self.lbl_cursor.pack(side="right")

    def _configure_tags(self):
        # Hidden tag (Synchronized name for both widgets)
        self.text_area.tag_config("hidden", elide=True)
        
        # Highlights
        self.text_area.tag_config("search_highlight", background="#D4AF37", foreground="black") 
        self.text_area.tag_config("search_current", background="#FF4500", foreground="white") 
        self.text_area.tag_config("has_note", underline=True)
        
        # User Marks
        self.text_area.tag_config("mark_red", background="#4a0e0e")    
        self.text_area.tag_config("mark_blue", background="#0e2a4a")   
        self.text_area.tag_config("mark_yellow", background="#4a4a0e") 
        
        # Syntax
        self.text_area.tag_config("syntax_error", foreground="#ff6b6b") 
        self.text_area.tag_config("syntax_warn", foreground="#ffa502")  
        self.text_area.tag_config("syntax_info", foreground="#7bed9f")  
        self.text_area.tag_config("syntax_debug", foreground="#70a1ff") 

    def _setup_proxy_events(self):
        """Hooks scrolling and inputs to sync line numbers."""
        tk_text = self.text_area._textbox
        
        # Scroll Sync
        def sync(*args):
            self.line_numbers.sync_scroll()
        
        tk_text.bind("<MouseWheel>", lambda e: self.after_idle(sync))
        tk_text.bind("<Button-4>", lambda e: self.after_idle(sync))
        tk_text.bind("<Button-5>", lambda e: self.after_idle(sync))
        
        # Override Scrollbar command (CustomTkinter specific)
        # We hook into the scrollbar callback if needed, but MouseWheel covers most use cases.
        
        # Interaction
        tk_text.bind("<KeyRelease>", self.on_ui_interaction)
        tk_text.bind("<ButtonRelease-1>", self.on_ui_interaction)
        tk_text.bind("<Control-MouseWheel>", self.on_zoom_scroll)
        self.text_area.bind("<Button-3>", self.show_context_menu)

    def on_ui_interaction(self, event=None):
        self.line_numbers.sync_scroll()
        self.update_cursor_info()

    def on_zoom_scroll(self, event):
        if event.delta > 0: self.change_font_size(1)
        else: self.change_font_size(-1)
        return "break"

    def change_font_size(self, delta):
        self.font_size += delta
        self.font_size = max(8, min(self.font_size, 30)) # Clamp between 8 and 30
        new_font = ("Consolas", self.font_size)
        self.text_area.configure(font=new_font)
        self.line_numbers.configure(font=new_font) 
        self.line_numbers.sync_scroll()

    def create_context_menu(self):
        self.context_menu = Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d")
        self.context_menu.add_command(label="🔍 Search on Google", command=self.search_google)
        self.context_menu.add_separator()
        color_menu = Menu(self.context_menu, tearoff=0, bg="#2b2b2b", fg="white")
        color_menu.add_command(label="Red", command=lambda: self.add_mark("mark_red", "red"))
        color_menu.add_command(label="Blue", command=lambda: self.add_mark("mark_blue", "blue"))
        color_menu.add_command(label="Yellow", command=lambda: self.add_mark("mark_yellow", "yellow"))
        self.context_menu.add_cascade(label="Mark as...", menu=color_menu)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Add Note", command=self.add_note_dialog)
        self.context_menu.add_command(label="Remove Mark", command=self.clear_mark)

    # --- Loading Logic ---
    def start_loading_file(self):
        threading.Thread(target=self._load_file_content, daemon=True).start()

    def _load_file_content(self):
        try:
            with open(self.file_path, 'rb') as f:
                raw = f.read(100000)
                enc = chardet.detect(raw)['encoding'] or 'utf-8'
            with open(self.file_path, 'r', encoding=enc, errors='replace') as f:
                content = f.read()
            self.after(0, lambda: self._update_text_area(content, enc))
        except Exception as e:
            self.after(0, lambda: self.lbl_status.configure(text=f"Error: {str(e)}", text_color="red"))

    def _update_text_area(self, content, encoding):
        self.text_area.configure(state="normal")
        self.text_area.insert("0.0", content)
        self._apply_syntax_coloring()
        self.text_area.configure(state="disabled")
        
        # Calculate lines
        try: self.total_lines = int(self.text_area.index('end-1c').split('.')[0])
        except: self.total_lines = 0
        
        self.line_numbers.populate(self.total_lines)
        self.update_status_label(encoding)

    def update_status_label(self, encoding="utf-8"):
        info = f"Ready ({encoding}) • {self.total_lines} lines"
        if self.file_path:
            try: fs = os.path.getsize(self.file_path) / 1024
            except: fs = 0
            info += f" • {fs:.1f} KB"
        if self.is_watching: info += " • 🔴 LIVE"
        self.lbl_status.configure(text=info, text_color="#2CC985" if not self.is_watching else "#ff4d4d")

    # --- Tail -f Logic ---
    def toggle_live_watch(self, active):
        self.is_watching = active
        self.update_status_label()
        if self.is_watching and self.file_path:
            threading.Thread(target=self._watch_loop, daemon=True).start()

    def _watch_loop(self):
        while self.is_watching and self.file_path:
            try:
                if not os.path.exists(self.file_path): break
                current_size = os.path.getsize(self.file_path)
                if current_size > self.last_file_size:
                    with open(self.file_path, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(self.last_file_size)
                        new_content = f.read()
                        self.last_file_size = current_size
                        if new_content:
                            self.after(0, lambda: self._append_content(new_content))
                time.sleep(2)
            except: break

    def _append_content(self, content):
        self.text_area.configure(state="normal")
        self.text_area.insert("end", content)
        self._apply_syntax_coloring()
        self.text_area.see("end")
        self.text_area.configure(state="disabled")
        
        # Update lines count and number widget
        try: self.total_lines = int(self.text_area.index('end-1c').split('.')[0])
        except: pass
        self.line_numbers.populate(self.total_lines)
        self.update_status_label()

    # --- Syntax & Styling ---
    def _apply_syntax_coloring(self):
        patterns = {
            "syntax_error": ["ERROR", "CRITICAL", "FATAL", "FAIL", "EXCEPTION"],
            "syntax_warn": ["WARN", "WARNING"],
            "syntax_info": ["INFO", "SUCCESS"],
            "syntax_debug": ["DEBUG", "TRACE"]
        }
        for tag, keywords in patterns.items():
            for kw in keywords:
                start_pos = "1.0"
                while True:
                    start_pos = self.text_area.search(kw, start_pos, stopindex="end", nocase=True)
                    if not start_pos: break
                    end_pos = f"{start_pos}+{len(kw)}c" 
                    self.text_area.tag_add(tag, start_pos, end_pos)
                    start_pos = end_pos

    def update_cursor_info(self):
        try:
            idx = self.text_area.index(tk.INSERT)
            row, col = idx.split('.')
            self.lbl_cursor.configure(text=f"Ln {row}, Col {int(col)+1}")
            meta = self.meta_data.get_annotation(row)
            self.lbl_note_display.configure(text=f"📝 {meta['note']}" if 'note' in meta else "")
        except: pass

    # --- Context Actions ---
    def show_context_menu(self, event):
        try: self.context_menu.tk_popup(event.x_root, event.y_root)
        finally: self.context_menu.grab_release()

    def search_google(self):
        try:
            sel = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            if sel: webbrowser.open(f"https://www.google.com/search?q={sel}")
        except: pass

    def add_mark(self, tag, color):
        line = self.text_area.index(tk.INSERT).split('.')[0]
        start, end = f"{line}.0", f"{line}.end"
        for t in ["mark_red", "mark_blue", "mark_yellow"]: self.text_area.tag_remove(t, start, end)
        self.text_area.tag_add(tag, start, end)
        self.meta_data.add_annotation(line, color=color)

    def clear_mark(self):
        line = self.text_area.index(tk.INSERT).split('.')[0]
        for t in ["mark_red", "mark_blue", "mark_yellow", "has_note"]:
            self.text_area.tag_remove(t, f"{line}.0", f"{line}.end")

    def add_note_dialog(self):
        line = self.text_area.index(tk.INSERT).split('.')[0]
        d = ctk.CTkInputDialog(text=f"Note for line {line}:", title="Add Note")
        txt = d.get_input()
        if txt:
            self.meta_data.add_annotation(line, note=txt)
            self.text_area.tag_add("has_note", f"{line}.0", f"{line}.end")
            self.lbl_note_display.configure(text=f"📝 {txt}")

    # --- Search & Filter Implementation ---
    def run_search(self, term, use_regex=False):
        self.text_area.tag_remove("search_highlight", "1.0", "end")
        self.text_area.tag_remove("search_current", "1.0", "end")
        self.search_matches = []
        self.current_match_index = -1
        
        if not term: return 0
        
        pos = "1.0"
        while True:
            # Tkinter search returns the start position
            # We use 'count' variable to get accurate match length, especially for Regex
            count_var = tk.IntVar()
            pos = self.text_area.search(term, pos, stopindex="end", nocase=True, regexp=use_regex, count=count_var)
            
            if not pos: break
            
            match_len = count_var.get()
            if match_len == 0: match_len = 1 # Safety fallback
            
            end = f"{pos}+{match_len}c"
            self.text_area.tag_add("search_highlight", pos, end)
            self.search_matches.append((pos, end))
            pos = end
            
        return len(self.search_matches)

    def cycle_matches(self, direction):
        if not self.search_matches: return 0, 0
        self.current_match_index += direction
        if self.current_match_index >= len(self.search_matches): self.current_match_index = 0
        elif self.current_match_index < 0: self.current_match_index = len(self.search_matches) - 1
        
        self.text_area.tag_remove("search_current", "1.0", "end")
        start, end = self.search_matches[self.current_match_index]
        self.text_area.tag_add("search_current", start, end)
        self.text_area.see(start)
        return self.current_match_index + 1, len(self.search_matches)

    def filter_by_term_only(self, term, use_regex=False):
        """Hides lines that do not contain the term in both Text area and Line Numbers."""
        self.text_area.configure(state="normal")
        self.line_numbers.configure(state="normal")
        
        # Reset visibility
        self.text_area.tag_remove("hidden", "1.0", "end")
        self.line_numbers.tag_remove("hidden", "1.0", "end")
        
        if not term:
            self._finalize_filter()
            return
            
        line_count = int(self.text_area.index('end-1c').split('.')[0])
        
        for i in range(1, line_count + 1):
            line_text = self.text_area.get(f"{i}.0", f"{i}.end")
            match = False
            try:
                if use_regex:
                    if re.search(term, line_text, re.IGNORECASE): match = True
                else:
                    if term.lower() in line_text.lower(): match = True
            except: pass # Regex error fallback
            
            if not match:
                self.text_area.tag_add("hidden", f"{i}.0", f"{i+1}.0")
                self.line_numbers.tag_add("hidden", f"{i}.0", f"{i+1}.0")
        
        self._finalize_filter()

    def apply_advanced_filter(self, levels, exclude_text):
        self.text_area.configure(state="normal")
        self.line_numbers.configure(state="normal")
        
        self.text_area.tag_remove("hidden", "1.0", "end")
        self.line_numbers.tag_remove("hidden", "1.0", "end")

        level_map = {
            "ERROR": ["ERROR", "CRITICAL", "FATAL", "FAIL", "EXCEPTION", "404", "500"],
            "WARN": ["WARN", "WARNING"],
            "INFO": ["INFO"],
            "DEBUG": ["DEBUG", "TRACE"]
        }
        allowed_keywords = []
        for lvl in levels: allowed_keywords.extend(level_map.get(lvl, []))
        
        line_count = int(self.text_area.index('end-1c').split('.')[0])
        for i in range(1, line_count + 1):
            line_text = self.text_area.get(f"{i}.0", f"{i}.end").upper()
            should_hide = False
            
            if exclude_text and exclude_text.upper() in line_text: should_hide = True
            if not should_hide and levels:
                if not any(k in line_text for k in allowed_keywords): should_hide = True
            
            if should_hide:
                self.text_area.tag_add("hidden", f"{i}.0", f"{i+1}.0")
                self.line_numbers.tag_add("hidden", f"{i}.0", f"{i+1}.0")
        
        self._finalize_filter()

    def _finalize_filter(self):
        self.text_area.configure(state="disabled")
        self.line_numbers.configure(state="disabled")
        # Ensure UI updates and scroll sync happens
        self.text_area.update_idletasks()
        self.line_numbers.sync_scroll()


# --- App Structure ---
class OmnilogApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        self.title("Omnilog v6.0 - The Gold Standard")
        self.geometry("1450x900")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.clipboard_counter = 1
        
        self._setup_sidebar()
        self._setup_main_area()
        self._setup_dnd()
        self._check_cli_args()

    def _check_cli_args(self):
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            if os.path.isfile(file_path):
                self.after(500, lambda: self.add_log_tab(file_path=file_path))

    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(30, weight=1)

        ctk.CTkLabel(self.sidebar, text="OMNILOG", font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        ctk.CTkButton(self.sidebar, text="📂 Open File", command=self.open_file_dialog).grid(row=1, column=0, padx=20, pady=5)
        ctk.CTkButton(self.sidebar, text="📋 From Clipboard", fg_color="#555", command=self.paste_from_clipboard).grid(row=2, column=0, padx=20, pady=5)

        ctk.CTkLabel(self.sidebar, text="Search & Navigation:", anchor="w").grid(row=3, column=0, padx=20, pady=(15,0), sticky="w")
        self.entry_search = ctk.CTkEntry(self.sidebar, placeholder_text="Type to search...")
        self.entry_search.grid(row=4, column=0, padx=20, pady=(5, 5))
        self.entry_search.bind("<KeyRelease>", self.on_search_typing)
        self.entry_search.bind("<Return>", self.on_search_enter_filter)
        
        self.chk_regex = ctk.CTkCheckBox(self.sidebar, text="Use Regex", font=("Arial", 11))
        self.chk_regex.grid(row=5, column=0, padx=20, pady=(0, 5), sticky="w")

        self.frame_nav = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.frame_nav.grid(row=6, column=0, padx=20, pady=0)
        self.btn_prev = ctk.CTkButton(self.frame_nav, text="<", width=30, command=lambda: self.navigate_search(-1))
        self.btn_prev.pack(side="left", padx=2)
        self.lbl_search_stats = ctk.CTkLabel(self.frame_nav, text="0 / 0", font=("Arial", 11), width=60)
        self.lbl_search_stats.pack(side="left", padx=5)
        self.btn_next = ctk.CTkButton(self.frame_nav, text=">", width=30, command=lambda: self.navigate_search(1))
        self.btn_next.pack(side="left", padx=2)

        self.combo_regex = ctk.CTkComboBox(self.sidebar, values=["Regex Presets...", "IP Address", "Email", "URL", "Date (YYYY-MM-DD)", "Error Codes"], command=self.apply_regex_preset)
        self.combo_regex.grid(row=7, column=0, padx=20, pady=(10, 10))

        ctk.CTkLabel(self.sidebar, text="Level Filter:", anchor="w", font=("Arial", 14, "bold")).grid(row=8, column=0, padx=20, pady=(15,5), sticky="w")
        self.chk_error = ctk.CTkCheckBox(self.sidebar, text="ERROR / CRITICAL", text_color="#ff6b6b")
        self.chk_error.grid(row=9, column=0, padx=20, pady=5, sticky="w")
        self.chk_warn = ctk.CTkCheckBox(self.sidebar, text="WARNING", text_color="#ffa502")
        self.chk_warn.grid(row=10, column=0, padx=20, pady=5, sticky="w")
        self.chk_info = ctk.CTkCheckBox(self.sidebar, text="INFO", text_color="#7bed9f")
        self.chk_info.grid(row=11, column=0, padx=20, pady=5, sticky="w")
        self.chk_debug = ctk.CTkCheckBox(self.sidebar, text="DEBUG", text_color="#70a1ff")
        self.chk_debug.grid(row=12, column=0, padx=20, pady=5, sticky="w")
        
        ctk.CTkLabel(self.sidebar, text="Exclude:", anchor="w").grid(row=13, column=0, padx=20, pady=(10,0), sticky="w")
        self.entry_exclude = ctk.CTkEntry(self.sidebar, placeholder_text="e.g. Heartbeat...")
        self.entry_exclude.grid(row=14, column=0, padx=20, pady=(5, 10))
        self.entry_exclude.bind("<Return>", lambda event: self.apply_sidebar_filter())
        self.btn_apply = ctk.CTkButton(self.sidebar, text="Apply Filter", fg_color="#444", command=self.apply_sidebar_filter)
        self.btn_apply.grid(row=15, column=0, padx=20, pady=5)

        ctk.CTkLabel(self.sidebar, text="View Control:", anchor="w", font=("Arial", 14, "bold")).grid(row=16, column=0, padx=20, pady=(15,5), sticky="w")
        frm_zoom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frm_zoom.grid(row=17, column=0)
        ctk.CTkButton(frm_zoom, text="Zoom -", width=60, command=lambda: self.change_zoom(-2)).pack(side="left", padx=5)
        ctk.CTkButton(frm_zoom, text="Zoom +", width=60, command=lambda: self.change_zoom(2)).pack(side="left", padx=5)
        self.sw_live = ctk.CTkSwitch(self.sidebar, text="🔴 Live Watch", command=self.toggle_live_watch)
        self.sw_live.grid(row=18, column=0, padx=20, pady=10)

        ctk.CTkLabel(self.sidebar, text="Tools:", anchor="w", font=("Arial", 14, "bold")).grid(row=19, column=0, padx=20, pady=(15,5), sticky="w")
        ctk.CTkButton(self.sidebar, text="📊 Statistics", fg_color="#2CC985", text_color="white", command=self.show_stats).grid(row=20, column=0, padx=20, pady=5)
        ctk.CTkButton(self.sidebar, text="📝 All Notes", fg_color="#D4AF37", text_color="white", command=self.show_notes_overview).grid(row=21, column=0, padx=20, pady=5)
        
        ctk.CTkButton(self.sidebar, text="❌ Close Tab", fg_color="#8B0000", hover_color="#B22222", text_color="white", command=self.close_current_tab).grid(row=22, column=0, padx=20, pady=(20, 5))
        ctk.CTkButton(self.sidebar, text="Export .JSON", fg_color="transparent", border_width=2, command=self.export_log_json).grid(row=23, column=0, padx=20, pady=5)
        ctk.CTkButton(self.sidebar, text="Export .TXT", fg_color="transparent", border_width=2, command=self.export_log_txt).grid(row=24, column=0, padx=20, pady=5)

    def _setup_main_area(self):
        self.tab_view = ctk.CTkTabview(self, anchor="nw")
        self.tab_view.grid(row=0, column=1, sticky="nsew", padx=10, pady=0)
        self.tab_view.add("Home")
        ctk.CTkLabel(self.tab_view.tab("Home"), text="Omnilog v6.0\nReady.", font=("Arial", 18), text_color="gray").place(relx=0.5, rely=0.5, anchor="center")

    def _setup_dnd(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.drop_file_handler)

    # Handlers
    def drop_file_handler(self, event): self.add_log_tab(file_path=event.data.strip('{}'))
    def open_file_dialog(self): 
        path = filedialog.askopenfilename()
        if path: self.add_log_tab(file_path=path)
    def paste_from_clipboard(self):
        try:
            content = self.clipboard_get()
            if not content: return
            self.clipboard_counter += 1
            self.add_log_tab(content=content, title=f"Clipboard #{self.clipboard_counter}")
        except: pass

    def add_log_tab(self, file_path=None, content=None, title=None):
        name = os.path.basename(file_path) if file_path else (title or "Untitled")
        try: self.tab_view.add(name)
        except: pass 
        self.tab_view.set(name)
        LogTab(self.tab_view.tab(name), file_path=file_path, content=content, title=name).pack(fill="both", expand=True)

    def _get_current_log_tab(self):
        cur = self.tab_view.get()
        if cur == "Home": return None
        for w in self.tab_view.tab(cur).winfo_children():
            if isinstance(w, LogTab): return w
        return None

    def close_current_tab(self):
        selected = self.tab_view.get()
        if selected == "Home": return
        try: self.tab_view.delete(selected)
        except: pass

    # Feature Proxies
    def on_search_typing(self, event):
        tab = self._get_current_log_tab()
        if tab: self.lbl_search_stats.configure(text=f"0 / {tab.run_search(self.entry_search.get(), bool(self.chk_regex.get()))}")
    
    def navigate_search(self, direction):
        tab = self._get_current_log_tab()
        if tab: 
            idx, total = tab.cycle_matches(direction)
            if total: self.lbl_search_stats.configure(text=f"{idx} / {total}")
            
    def on_search_enter_filter(self, event):
        tab = self._get_current_log_tab()
        if tab: tab.filter_by_term_only(self.entry_search.get(), bool(self.chk_regex.get()))

    def apply_regex_preset(self, choice):
        presets = {
            "IP Address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "Email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "URL": r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",
            "Date (YYYY-MM-DD)": r"\d{4}-\d{2}-\d{2}",
            "Error Codes": r"0x[0-9A-Fa-f]+"
        }
        if choice in presets:
            self.entry_search.delete(0, tk.END)
            self.entry_search.insert(0, presets[choice])
            self.chk_regex.select()
            self.on_search_typing(None)

    def change_zoom(self, delta):
        tab = self._get_current_log_tab()
        if tab: tab.change_font_size(delta)

    def toggle_live_watch(self):
        tab = self._get_current_log_tab()
        if tab: tab.toggle_live_watch(bool(self.sw_live.get()))

    def apply_sidebar_filter(self):
        tab = self._get_current_log_tab()
        if tab:
            active = []
            if self.chk_error.get(): active.append("ERROR")
            if self.chk_warn.get(): active.append("WARN")
            if self.chk_info.get(): active.append("INFO")
            if self.chk_debug.get(): active.append("DEBUG")
            tab.apply_advanced_filter(active, self.entry_exclude.get())

    def export_log_json(self):
        tab = self._get_current_log_tab()
        if tab:
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile=f"{tab.file_name}_audit.json")
            if path:
                with open(path, 'w', encoding='utf-8') as f: json.dump({"filename": tab.file_name, "annotations": tab.meta_data.annotations}, f, indent=4)

    def export_log_txt(self):
        tab = self._get_current_log_tab()
        if tab:
            path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")], initialfile=f"{tab.file_name}.txt")
            if path:
                with open(path, 'w', encoding='utf-8') as f: f.write(tab.text_area.get("1.0", "end-1c"))
                messagebox.showinfo("Export", "File saved.")

    def show_stats(self):
        tab = self._get_current_log_tab()
        if not tab: return
        content = tab.text_area.get("1.0", "end")
        counts = Counter()
        patterns = {"ERROR": r'ERROR|CRITICAL|FATAL|FAIL', "WARN": r'WARN|WARNING', "INFO": r'INFO', "DEBUG": r'DEBUG'}
        for line in content.split('\n'):
            for k, v in patterns.items():
                if re.search(v, line, re.IGNORECASE): 
                    counts[k] += 1; break
        if sum(counts.values()) == 0: 
            messagebox.showinfo("Stats", "No log levels found."); return
        win = ctk.CTkToplevel(self); win.geometry("600x500"); win.title(f"Stats: {tab.file_name}")
        fig, ax = plt.subplots(figsize=(5, 4)); fig.patch.set_facecolor('#2b2b2b'); ax.set_facecolor('#2b2b2b')
        bars = ax.bar(counts.keys(), counts.values(), color=['#ff6b6b', '#ffa502', '#7bed9f', '#70a1ff'])
        ax.tick_params(colors='white'); ax.spines['bottom'].set_color('white'); ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        for bar in bars: ax.annotate(f'{bar.get_height()}', (bar.get_x()+bar.get_width()/2, bar.get_height()), xytext=(0,3), textcoords="offset points", ha='center', color='white')
        FigureCanvasTkAgg(fig, master=win).get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def show_notes_overview(self):
        tab = self._get_current_log_tab()
        if not tab: return
        notes = tab.meta_data.get_all_notes()
        if not notes: messagebox.showinfo("Notes", "No notes found."); return
        win = ctk.CTkToplevel(self); win.geometry("500x400"); win.title(f"Notes: {tab.file_name}")
        sf = ctk.CTkScrollableFrame(win); sf.pack(fill="both", expand=True, padx=10, pady=10)
        for k in sorted(notes.keys(), key=lambda x: int(x)):
            c = ctk.CTkFrame(sf, fg_color="#333"); c.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(c, text=f"Line {k}", font=("Arial",12,"bold"), text_color="#D4AF37").pack(anchor="w", padx=10)
            ctk.CTkLabel(c, text=notes[k]['note'], font=("Arial",12), text_color="#eee").pack(anchor="w", padx=10)

if __name__ == "__main__":
    app = OmnilogApp()
    app.mainloop()
