import customtkinter as ctk
import os
import subprocess
import sys
import tkinter as tk # Needed for text tags (coloring)
import shutil  # To copy files
import json    # To read the problem data
import re      # To find the data inside HTML
from tkinter import filedialog  # To open the "Select File" window
from tkinter import messagebox # For the confirmation pop-up

# Import our logic modules
import database_manager as db
import gamification as game
import test_runner as runner
import visualizer as viz

# Constants
SOLUTIONS_DIR = "solutions"

# --- APP CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class DSAApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        db.add_notes_column()

        # 1. Window Setup
        self.title("DSA Progress Tracker")
        self.geometry("1200x800")

        # Fonts
        self.header_font = ("DejaVu Sans", 22, "bold")
        self.ui_font = ("DejaVu Sans", 12)
        
        # Console Font (Mutable for zooming)
        self.console_font_name = "DejaVu Sans Mono"
        self.console_font_size = 12
        self.console_font = ctk.CTkFont(family=self.console_font_name, size=self.console_font_size)

        # 2. Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 3. Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="DSA TRACKER", font=("DejaVu Sans", 20, "bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.sidebar_btn_1 = ctk.CTkButton(self.sidebar_frame, text="Dashboard", font=self.ui_font, command=self.show_dashboard_view)
        self.sidebar_btn_1.grid(row=1, column=0, padx=20, pady=10)

        self.sidebar_btn_2 = ctk.CTkButton(self.sidebar_frame, text="My Stats", font=self.ui_font, command=self.show_stats_view)
        self.sidebar_btn_2.grid(row=2, column=0, padx=20, pady=10)

        # (Inside __init__, below sidebar_btn_2)
        self.sidebar_btn_3 = ctk.CTkButton(self.sidebar_frame, text="🗑️ Recycle Bin", 
                                           font=self.ui_font, fg_color="#546E7A", hover_color="#455A64",
                                           command=self.show_recycle_bin_view)
        self.sidebar_btn_3.grid(row=3, column=0, padx=20, pady=10)

        self.level_label = ctk.CTkLabel(self.sidebar_frame, text="Loading...", font=self.ui_font, justify="left")
        self.level_label.grid(row=5, column=0, padx=20, pady=20)

        # 4. Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # 5. Start
        self.update_sidebar_stats()
        self.show_dashboard_view()
    
    

    # --- LOGIC: ADD PROBLEMS ---
# --- LOGIC: ADD PROBLEMS ---
# --- LOGIC: ADD PROBLEMS ---
    def add_new_problems(self):
        """Opens the native OS file picker. Respects 'Cancel' without showing fallback."""
        
        file_paths = []
        use_fallback = True  # Assume we need the ugly picker unless proven otherwise

        # 1. Try Native Linux Picker (Zenity)
        if sys.platform == "linux":
            try:
                cmd = [
                    'zenity', '--file-selection', '--multiple', 
                    '--separator=|', '--title=Select Problem HTML Files',
                    '--file-filter=HTML Files | *.html'
                ]
                # We run this to check if Zenity exists and what the user does
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                # If we reached this line, Zenity exists and ran.
                # We disable fallback immediately so the ugly box NEVER appears on Linux.
                use_fallback = False 
                
                if result.returncode == 0 and result.stdout.strip():
                    file_paths = result.stdout.strip().split('|')
                # If result.returncode != 0, it means User Cancelled. 
                # Since use_fallback is False, we will just exit peacefully.
                
            except FileNotFoundError:
                # Only if 'zenity' is not installed do we allow the fallback
                print("Zenity not found. Using standard picker.")
                use_fallback = True

        # 2. Standard Picker (Windows/Mac OR Linux without Zenity)
        if use_fallback: 
            file_paths = filedialog.askopenfilenames(
                title="Select Problem HTML Files",
                filetypes=[("HTML Files", "*.html")]
            )

        if not file_paths:
            return  # User cancelled (in either picker)

        # --- IMPORT LOGIC ---
        # Ensure questions directory exists
        if not os.path.exists("questions"):
            os.makedirs("questions")

        imported_count = 0
        for src_path in file_paths:
            try:
                src_path = src_path.strip()
                filename = os.path.basename(src_path)
                dest_path = os.path.join("questions", filename)
                
                if os.path.abspath(src_path) != os.path.abspath(dest_path):
                    shutil.copy(src_path, dest_path)

                with open(dest_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                match = re.search(r'const quizData = ({.*?});', content, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    title = data['title']
                    clean_name = re.sub(r'^\d+\s*', '', title) 
                    clean_name = re.sub(r'[^\w\s-]', '', clean_name).strip().replace(' ', '_') + ".py"
                    cleanr = re.compile('<.*?>')
                    instructions = re.sub(cleanr, '', data['instructions']).strip()
                    solution_stub = data['solutions'][0]['content'].split('\n')[0] + "\n    pass\n"
                    test_code = data['tests'][0]['content']
                    
                    db.upsert_problem(title, clean_name, instructions, solution_stub, test_code)
                    imported_count += 1
                    
            except Exception as e:
                print(f"Failed to import {filename}: {e}")

        if imported_count > 0:
            print(f"Imported {imported_count} files.")
            self.refresh_problem_list()

    def update_sidebar_stats(self):
        stats = db.get_user_stats()
        if stats:
            xp, level, streak = stats
            text = f"Lvl {level}\nXP: {xp}\nStreak: {streak}"
        else:
            text = "Level 1"
        self.level_label.configure(text=text)

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    # --- VIEW: DASHBOARD ---
    # --- VIEW: DASHBOARD ---
    def show_dashboard_view(self):
        self.clear_main_frame()
        self.update_sidebar_stats()

        # Init Select Mode state if not exists
        if not hasattr(self, 'select_mode'):
            self.select_mode = False
        self.selected_problems = set() # Stores IDs of checked problems

        # Header Row
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(header_frame, text="Problem Dashboard", font=self.header_font)
        title.pack(side="left")

        # CONTROLS CONTAINER (Right side of header)
        controls = ctk.CTkFrame(header_frame, fg_color="transparent")
        controls.pack(side="right")

        # 1. Search Bar
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_dashboard)
        search_entry = ctk.CTkEntry(controls, placeholder_text="🔍 Search...", 
                                    width=200, textvariable=self.search_var, font=self.ui_font)
        search_entry.pack(side="right", padx=(10, 0))

        # 2. Select Mode Switch
        self.mode_switch = ctk.CTkSwitch(controls, text="Edit Mode", command=self.toggle_select_mode)
        # Set switch state based on current mode
        if self.select_mode: self.mode_switch.select()
        else: self.mode_switch.deselect()
        self.mode_switch.pack(side="right", padx=10)

        # 3. Dynamic Action Button (Add vs Delete)
        if self.select_mode:
            self.action_btn = ctk.CTkButton(header_frame, text="🗑️ Delete Selected", width=120, 
                                fg_color="#F44336", hover_color="#D32F2F",
                                command=self.delete_selected_problems)
        else:
            self.action_btn = ctk.CTkButton(header_frame, text="➕ Add Problems", width=120, 
                                fg_color="#2196F3", hover_color="#1976D2",
                                command=self.add_new_problems)
        self.action_btn.pack(side="left", padx=20)

        # Scrollable List
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Available Problems")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.refresh_problem_list()

    def toggle_select_mode(self):
        """Toggles between Solving Mode and Edit (Delete) Mode."""
        self.select_mode = self.mode_switch.get() == 1
        self.selected_problems.clear() # Reset selection
        self.show_dashboard_view() # Re-render header and list

    def refresh_problem_list(self, filter_query=""):
        if not hasattr(self, 'scroll_frame') or not self.scroll_frame: return

        # Clear List
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # Fetch Data
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT id, title, is_solved FROM problems")
        rows = c.fetchall()
        conn.close()

        for problem in rows:
            pid, title, is_solved = problem
            
            if filter_query and filter_query not in title.lower(): continue

            card = ctk.CTkFrame(self.scroll_frame)
            card.pack(fill="x", pady=5)
            
            # --- DISPLAY LOGIC BASED ON MODE ---
            if self.select_mode:
                # CHECKBOX for selection
                chk = ctk.CTkCheckBox(card, text="", width=24, command=lambda p=pid: self.toggle_selection(p))
                chk.pack(side="left", padx=10, pady=10)
                
                # Title
                ctk.CTkLabel(card, text=f"{pid}. {title}", font=("DejaVu Sans", 14)).pack(side="left", padx=5)
            else:
                # NORMAL MODE (Status Icon + Buttons)
                status_text = "✔" if is_solved else "⚫"
                status_color = "#4CAF50" if is_solved else "#9E9E9E"
                ctk.CTkLabel(card, text=status_text, font=("DejaVu Sans Mono", 16), text_color=status_color).pack(side="left", padx=10, pady=10)
                ctk.CTkLabel(card, text=f"{pid}. {title}", font=("DejaVu Sans", 14)).pack(side="left", padx=5)
                
                btn_text = "Review" if is_solved else "Solve"
                ctk.CTkButton(card, text=btn_text, width=80, command=lambda p=pid: self.open_solver_view(p)).pack(side="right", padx=10)

    def toggle_selection(self, pid):
        """Tracks which items are checked."""
        if pid in self.selected_problems:
            self.selected_problems.remove(pid)
        else:
            self.selected_problems.add(pid)
        
        # Optional: Update delete button text to show count e.g. "Delete (3)"
        count = len(self.selected_problems)
        new_text = f"🗑️ Delete ({count})" if count > 0 else "🗑️ Delete Selected"
        self.action_btn.configure(text=new_text)

    # --- LOGIC: DELETE ---
    # --- LOGIC: DELETE ---
    def delete_selected_problems(self):
        if not self.selected_problems:
            return

        # 1. Confirmation Pop-up
        count = len(self.selected_problems)
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {count} problems?\nThis will move files to the Recycle Bin."):
            return

        # 2. Ensure Recycle Bin exists
        recycle_dir = "recycle_bin"
        if not os.path.exists(recycle_dir):
            os.makedirs(recycle_dir)

        conn = db.get_connection()
        c = conn.cursor()
        
        deleted_count = 0

        for pid in self.selected_problems:
            # Get info to find the files
            c.execute("SELECT title, filename FROM problems WHERE id = ?", (pid,))
            row = c.fetchone()
            
            if row:
                title, py_filename = row
                
                # --- A. Move Python Solution (The "Notebook") ---
                # This might not exist if you haven't clicked "Solve" yet.
                py_path = os.path.join("solutions", py_filename)
                if os.path.exists(py_path):
                    try:
                        shutil.move(py_path, os.path.join(recycle_dir, py_filename))
                    except Exception as e:
                        print(f"Error moving solution {py_filename}: {e}")

                # --- B. Move HTML Question (The "Textbook") ---
                # We scan the 'questions' folder to find the HTML file with the matching Title.
                if os.path.exists("questions"):
                    for html_file in os.listdir("questions"):
                        if not html_file.endswith(".html"): continue
                        
                        full_html_path = os.path.join("questions", html_file)
                        try:
                            # Read file to check Title
                            with open(full_html_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Extract JSON to match Title
                            match = re.search(r'const quizData = ({.*?});', content, re.DOTALL)
                            if match:
                                data = json.loads(match.group(1))
                                if data['title'] == title:
                                    # FOUND IT! Move HTML to Recycle Bin
                                    shutil.move(full_html_path, os.path.join(recycle_dir, html_file))
                                    break 
                        except Exception as e:
                            print(f"Error checking HTML {html_file}: {e}")

            # C. Delete from DB
            db.delete_problem(pid)
            deleted_count += 1

        conn.close()
        
        messagebox.showinfo("Success", f"Moved {deleted_count} problems to Recycle Bin.")
        self.toggle_select_mode() # Reset mode
        self.refresh_problem_list() # Force refresh

    def filter_dashboard(self, *args):
        """Called whenever the user types in the search bar."""
        query = self.search_var.get().lower()
        self.refresh_problem_list(filter_query=query)



    # --- VIEW: STATS (Menu) ---
    def show_stats_view(self):
        self.clear_main_frame()
        title = ctk.CTkLabel(self.main_frame, text="My Progress Statistics", font=self.header_font)
        title.pack(pady=20)
        
        info = ctk.CTkLabel(self.main_frame, text="Choose a visualization tool:", font=self.ui_font)
        info.pack(pady=10)

        # Graph Button
        btn_graph = ctk.CTkButton(self.main_frame, text="📊 Generate Progress Graph", 
                            font=self.ui_font, height=50, width=300, fg_color="#4CAF50", hover_color="#388E3C",
                            command=viz.generate_progress_graph)
        btn_graph.pack(pady=20)
        
        # History Table Button (NEW)
        btn_hist = ctk.CTkButton(self.main_frame, text="📜 View Full History Table", 
                            font=self.ui_font, height=50, width=300, fg_color="#2196F3", hover_color="#1976D2",
                            command=self.show_global_history_view)
        btn_hist.pack(pady=10)

    # --- VIEW: GLOBAL HISTORY TABLE (NEW) ---
    def show_global_history_view(self):
        self.clear_main_frame()
        
        # Header
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(header_frame, text="<- Back", width=60, command=self.show_stats_view).pack(side="left")
        ctk.CTkLabel(header_frame, text="Global Performance History", font=self.header_font).pack(side="left", padx=20)
        
        # Data Fetch
        stats = db.get_global_stats()
        
        # Scrollable Table Container
        table_frame = ctk.CTkScrollableFrame(self.main_frame)
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Table Headers
        headers = ["Problem Name", "Wins", "Fails", "Last Attempt"]
        header_row = ctk.CTkFrame(table_frame, fg_color="#333333")
        header_row.pack(fill="x", pady=2)
        
        # Grid Configuration for Columns
        header_row.columnconfigure(0, weight=3) # Name is wider
        header_row.columnconfigure(1, weight=1)
        header_row.columnconfigure(2, weight=1)
        header_row.columnconfigure(3, weight=2) # Date is wide
        
        for i, h in enumerate(headers):
            ctk.CTkLabel(header_row, text=h, font=("DejaVu Sans", 12, "bold")).grid(row=0, column=i, padx=5, pady=5, sticky="ew")

        # Table Rows
        for row_data in stats:
            title, wins, losses, last_date = row_data
            wins = wins if wins else 0
            losses = losses if losses else 0
            date_display = str(last_date).split('.')[0] if last_date else "Never"
            
            row = ctk.CTkFrame(table_frame)
            row.pack(fill="x", pady=2)
            row.columnconfigure(0, weight=3)
            row.columnconfigure(1, weight=1)
            row.columnconfigure(2, weight=1)
            row.columnconfigure(3, weight=2)
            
            ctk.CTkLabel(row, text=title, anchor="w").grid(row=0, column=0, padx=10, pady=5, sticky="ew")
            ctk.CTkLabel(row, text=str(wins), text_color="#4CAF50").grid(row=0, column=1, padx=5, pady=5) # Green Wins
            ctk.CTkLabel(row, text=str(losses), text_color="#F44336").grid(row=0, column=2, padx=5, pady=5) # Red Losses
            ctk.CTkLabel(row, text=date_display).grid(row=0, column=3, padx=5, pady=5)

    # --- VIEW: SOLVER ---
    def open_solver_view(self, problem_id):
        self.clear_main_frame()
        
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT title, instructions, filename, solution_stub, test_code, is_solved FROM problems WHERE id = ?", (problem_id,))
        data = c.fetchone()
        conn.close()
        
        if not data: return
        title, instructions, filename, stub, test_code, is_solved = data
        
        full_path = os.path.join(SOLUTIONS_DIR, filename)
        if not os.path.exists(full_path):
            with open(full_path, 'w') as f:
                f.write(f"# {title}\n{stub}")

        # HEADER
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(header, text="<- Back", width=60, command=self.show_dashboard_view).pack(side="left")
        ctk.CTkLabel(header, text=f"{title}", font=self.header_font).pack(side="left", padx=20)

        # CONTENT AREA
        content = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # LEFT: Instructions
        left_pane = ctk.CTkFrame(content)
        left_pane.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(left_pane, text="Instructions:", font=("DejaVu Sans", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        instr_box = ctk.CTkTextbox(left_pane, wrap="word", font=("DejaVu Sans", 13))
        instr_box.pack(fill="both", expand=True, padx=10, pady=10)
        instr_box.insert("0.0", instructions)
        instr_box.configure(state="disabled")

       # RIGHT: Actions & Console/Notes
        right_pane = ctk.CTkFrame(content, width=400)
        right_pane.pack(side="right", fill="y", padx=(10, 0))

        # --- ACTIONS SECTION ---
        ctk.CTkLabel(right_pane, text="Actions", font=("DejaVu Sans", 14, "bold")).pack(pady=10)
        
        ctk.CTkButton(right_pane, text="Open in VS Code", fg_color="#E0E0E0", text_color="black", hover_color="#D6D6D6",
                      command=lambda: self.open_in_editor(full_path)).pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(right_pane, text="↺ Reset Code", fg_color="#D32F2F", hover_color="#B71C1C",
                      command=lambda: self.reset_code(problem_id, filename)).pack(fill="x", padx=10, pady=5)
        
        run_btn = ctk.CTkButton(right_pane, text="▶ Run Tests", fg_color="green", hover_color="darkgreen",
                                command=lambda: self.run_tests_gui(problem_id, filename, test_code, self.console_box, is_solved))
        run_btn.pack(fill="x", padx=10, pady=15)
        
        ctk.CTkButton(right_pane, text="📜 View Mistake Log", fg_color="#FF9800", hover_color="#F57C00",
                      command=lambda: self.show_history(problem_id, self.console_box)).pack(fill="x", padx=10, pady=5)

        # --- TABS: CONSOLE & NOTES ---
        self.tab_view = ctk.CTkTabview(right_pane)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create Tabs
        tab_console = self.tab_view.add("Test Results")
        tab_notes = self.tab_view.add("My Notes")
        
        # TAB 1: CONSOLE (Moved logic here)
        # Zoom controls inside the tab
        console_controls = ctk.CTkFrame(tab_console, fg_color="transparent", height=30)
        console_controls.pack(fill="x")
        ctk.CTkButton(console_controls, text="+", width=30, command=self.zoom_in).pack(side="right", padx=2)
        ctk.CTkButton(console_controls, text="-", width=30, command=self.zoom_out).pack(side="right", padx=2)

        self.console_box = ctk.CTkTextbox(tab_console, font=self.console_font, fg_color="#1e1e1e", text_color="#d4d4d4")
        self.console_box.pack(fill="both", expand=True)
        self.console_box.insert("0.0", "Ready.\n")
        self.console_box.configure(state="disabled")
        self.console_box.tag_config("pass", foreground="#4CAF50")
        self.console_box.tag_config("fail", foreground="#F44336")
        self.console_box.tag_config("info", foreground="#2196F3")

        # TAB 2: NOTES
        self.notes_box = ctk.CTkTextbox(tab_notes, font=("DejaVu Sans", 12))
        self.notes_box.pack(fill="both", expand=True, pady=(0, 10))
        
        # Load existing notes
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT user_notes FROM problems WHERE id = ?", (problem_id,))
        saved_notes = c.fetchone()[0]
        conn.close()
        if saved_notes:
            self.notes_box.insert("0.0", saved_notes)
            
        # Save Button
        ctk.CTkButton(tab_notes, text="💾 Save Notes", height=30, 
                      command=lambda: self.save_notes_gui(problem_id)).pack(fill="x")

    # --- ZOOM LOGIC ---
    def zoom_in(self):
        self.console_font_size += 2
        self.update_console_font()

    def zoom_out(self):
        if self.console_font_size > 8:
            self.console_font_size -= 2
        self.update_console_font()

    def update_console_font(self):
        new_font = ctk.CTkFont(family=self.console_font_name, size=self.console_font_size)
        self.console_box.configure(font=new_font)

    # --- LOGIC INTEGRATION ---
    def open_in_editor(self, filepath):
        try:
            if sys.platform == "linux":
                subprocess.call(["xdg-open", filepath])
            elif sys.platform == "win32":
                os.startfile(filepath)
            elif sys.platform == "darwin":
                subprocess.call(["open", filepath])
        except Exception as e:
            print(f"Error: {e}")

    def run_tests_gui(self, problem_id, filename, test_code, console, was_solved):
        console.configure(state="normal")
        console.delete("0.0", "end")
        console.insert("0.0", "Running tests...\n", "info")
        console.update()

        result = runner.run_test_module(test_code, filename)
        
        # Color Coded Output
        if result['success']:
            console.insert("end", "\n[SUCCESS]\n", "pass")
            console.insert("end", result['message'] + "\n")
            
            if not was_solved:
                reward = game.award_xp(problem_id)
                console.insert("end", reward, "pass")
                self.update_sidebar_stats()
        else:
            console.insert("end", "\n[FAILED]\n", "fail")
            # We strip the ugly traceback and show just the message
            clean_msg = result['message'].replace("❌", "").replace("FAIL:", ">>")
            console.insert("end", clean_msg, "fail")

        db.log_attempt(problem_id, result['success'], result['message'])
        console.configure(state="disabled")

    def show_history(self, problem_id, console):
        history = db.get_problem_history(problem_id)
        console.configure(state="normal")
        console.delete("0.0", "end")
        
        if not history:
            console.insert("0.0", "No attempts yet.", "info")
        else:
            console.insert("end", f"HISTORY ({len(history)} attempts)\n\n", "info")
            for attempt in history:
                timestamp, success, error_msg = attempt
                time_str = str(timestamp).split('.')[0]
                
                if success:
                    console.insert("end", f"✔ {time_str}: SOLVED\n", "pass")
                else:
                    console.insert("end", f"✘ {time_str}: FAILED\n", "fail")
                    # Clean up error msg
                    short_err = error_msg.split('\n')[0] if error_msg else "Unknown Error"
                    console.insert("end", f"   {short_err}...\n", "fail")
                console.insert("end", "-"*20 + "\n")

        console.configure(state="disabled")

    # --- VIEW: RECYCLE BIN ---
    # --- VIEW: RECYCLE BIN ---
    def show_recycle_bin_view(self):
        self.clear_main_frame()
        
        # Header
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(header, text="Recycle Bin", font=self.header_font).pack(side="left")
        
        # Folder check
        recycle_dir = "recycle_bin"
        if not os.path.exists(recycle_dir):
            os.makedirs(recycle_dir)
            
        # FIX: Look for BOTH .py and .html files
        files = [f for f in os.listdir(recycle_dir) if f.endswith('.py') or f.endswith('.html')]
        files.sort()
        
        if not files:
            ctk.CTkLabel(self.main_frame, text="Recycle Bin is empty.", font=self.ui_font, text_color="gray").pack(pady=50)
            return

        # Scroll List
        scroll = ctk.CTkScrollableFrame(self.main_frame, label_text="Deleted Files")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        for f in files:
            row = ctk.CTkFrame(scroll)
            row.pack(fill="x", pady=5)
            
            # Icon based on type (Snake for Python, Paper for HTML)
            icon = "🐍" if f.endswith('.py') else "📄"
            ctk.CTkLabel(row, text=f"{icon} {f}", font=("DejaVu Sans Mono", 14)).pack(side="left", padx=10, pady=10)
            
            # Buttons
            ctk.CTkButton(row, text="♻ Restore", width=80, fg_color="#4CAF50", hover_color="#388E3C",
                          command=lambda name=f: self.restore_file(name)).pack(side="right", padx=5)
            
            ctk.CTkButton(row, text="✖ Delete", width=80, fg_color="#F44336", hover_color="#D32F2F",
                          command=lambda name=f: self.permanently_delete(name)).pack(side="right", padx=5)

    def restore_file(self, filename):
        """Restores file to its correct folder (questions/ or solutions/) and updates DB."""
        src = os.path.join("recycle_bin", filename)
        
        try:
            # CASE A: Restoring an HTML Question File
            if filename.endswith(".html"):
                dst = os.path.join("questions", filename)
                shutil.move(src, dst)
                # Parse it to re-add to DB
                self.process_restore_html(dst, None) # None = Let it guess the python filename
                messagebox.showinfo("Success", f"Restored Question '{filename}'!\nIt is back on the Dashboard.")

            # CASE B: Restoring a Python Solution File
            elif filename.endswith(".py"):
                dst = os.path.join("solutions", filename)
                shutil.move(src, dst)
                
                # We need to find the matching HTML in 'questions/' to get the metadata
                html_found = False
                
                # Attempt to find matching HTML
                if os.path.exists("questions"):
                    # 1. Try simple name match (Square.py -> Square.html)
                    simple_html = filename.replace('.py', '.html')
                    if os.path.exists(os.path.join("questions", simple_html)):
                        self.process_restore_html(os.path.join("questions", simple_html), filename)
                        html_found = True
                    else:
                        # 2. Harder search: Scan all HTMLs for title match (Backup plan)
                        # (Simplified for now to rely on Case A being done first usually)
                        pass 

                if html_found:
                    messagebox.showinfo("Success", f"Restored Solution '{filename}'!")
                else:
                    messagebox.showwarning("Partial Restore", 
                        f"Restored code '{filename}' to solutions folder.\n"
                        "However, could not find matching HTML file in 'questions/' folder to add it to DB.\n"
                        "Tip: You might need to restore the .html file from Recycle Bin first!")

            self.show_recycle_bin_view() # Refresh view
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore: {e}")

    def process_restore_html(self, html_path, force_py_filename=None):
        """Helper to parse HTML and insert into DB."""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            match = re.search(r'const quizData = ({.*?});', content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                title = data['title']
                
                # Determine Python filename
                if force_py_filename:
                    py_filename = force_py_filename
                else:
                    # Generate standard name
                    clean_name = re.sub(r'^\d+\s*', '', title) 
                    py_filename = re.sub(r'[^\w\s-]', '', clean_name).strip().replace(' ', '_') + ".py"
                
                cleanr = re.compile('<.*?>')
                instructions = re.sub(cleanr, '', data['instructions']).strip()
                test_code = data['tests'][0]['content']
                stub = "pass" # Default stub
                
                db.upsert_problem(title, py_filename, instructions, stub, test_code)
        except Exception as e:
            print(f"Error parsing HTML during restore: {e}")

    def permanently_delete(self, filename):
        """Deletes the file forever."""
        if not messagebox.askyesno("Confirm", f"Permanently delete '{filename}'?"):
            return
            
        try:
            os.remove(os.path.join("recycle_bin", filename))
            self.show_recycle_bin_view()
        except Exception as e:
            print(f"Error: {e}")


    # --- LOGIC: RESET CODE ---
    def reset_code(self, problem_id, filename):
        """Resets the solution file to the original starter stub."""
        # 1. Ask for confirmation so you don't delete good code by accident
        if not messagebox.askyesno("Confirm Reset", "Are you sure? This will delete your current code and restore the starter template."):
            return

        # 2. Fetch original stub from Database
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT title, solution_stub FROM problems WHERE id = ?", (problem_id,))
        row = c.fetchone()
        conn.close()

        # 3. Overwrite the file
        if row:
            title, stub = row
            full_path = os.path.join(SOLUTIONS_DIR, filename)
            
            try:
                with open(full_path, 'w') as f:
                    f.write(f"# {title}\n{stub}")
                
                messagebox.showinfo("Success", "Code reset to default template.")
                
                # Update Console to show it happened
                self.console_box.configure(state="normal")
                self.console_box.insert("end", "\n[RESET] Code restored to template.\n", "info")
                self.console_box.configure(state="disabled")
            except Exception as e:
                messagebox.showerror("Error", f"Could not reset file: {e}")

                
    def save_notes_gui(self, problem_id):
        text = self.notes_box.get("0.0", "end").strip()
        db.save_problem_notes(problem_id, text)
        messagebox.showinfo("Saved", "Notes updated successfully!")
if __name__ == "__main__":
    db.init_db()
    app = DSAApp()
    app.mainloop()