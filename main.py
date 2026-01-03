import os
import re
import json
import time # <--- FOR TIMER
import database_manager as db
import test_runner as runner
import gamification as game
import quality_check as qc  # <--- NEW
import reviewer as rev      # <--- NEW
import visualizer as viz  # <--- NEW IMPORT

HTML_EXTENSION = ".html"

# Update the Configuration at the top
QUESTIONS_DIR = "questions"  # <--- New constant
HTML_EXTENSION = ".html"

def sync_html_files():
    """Scans for HTML files in the 'questions' folder and sends data to DB."""
    
    # Check if directory exists
    if not os.path.exists(QUESTIONS_DIR):
        print(f"⚠️ Warning: '{QUESTIONS_DIR}' folder not found.")
        return

    # List files in the subdirectory
    files = [f for f in os.listdir(QUESTIONS_DIR) if f.endswith(HTML_EXTENSION)]
    
    for f in files:
        # Build the full path (e.g., "questions/001 Square.html")
        full_path = os.path.join(QUESTIONS_DIR, f)
        
        with open(full_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        match = re.search(r'const quizData = ({.*?});', content, re.DOTALL)
        if not match: continue
        
        try:
            data = json.loads(match.group(1))
            title = data['title']
            clean_name = re.sub(r'^\d+\s*', '', title) 
            clean_name = re.sub(r'[^\w\s-]', '', clean_name)
            clean_name = clean_name.strip().replace(' ', '_') + ".py"
            cleanr = re.compile('<.*?>')
            instructions = re.sub(cleanr, '', data['instructions']).strip()
            solution_stub = data['solutions'][0]['content'].split('\n')[0] + "\n    pass\n"
            test_code = data['tests'][0]['content']
            
            db.upsert_problem(title, clean_name, instructions, solution_stub, test_code)
        except json.JSONDecodeError:
            continue

def show_history_stats():
    """Displays global stats."""
    stats = db.get_global_stats()
    print("\n" + "="*80)
    print(f"📜  GLOBAL HISTORY & PERFORMANCE STATS")
    print("="*80)
    print(f"{'PROBLEM NAME':<35} | {'WINS':<6} | {'FAILS':<6} | {'LAST ATTEMPT'}")
    print("-" * 80)
    for row in stats:
        title, wins, losses, last_date = row
        wins = wins if wins else 0
        losses = losses if losses else 0
        date_display = str(last_date).split('.')[0] if last_date else "Never"
        print(f"{title:<35} | {wins:<6} | {losses:<6} | {date_display}")
    input("\nPress [ENTER] to return...")

def show_dashboard():
    """Displays dashboard with Review Notification."""
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM problems")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM problems WHERE is_solved = 1")
    solved = c.fetchone()[0]
    
    # Check for Reviews
    due_problems = rev.get_due_problems()
    review_msg = f" | 🔔 Review Due: {len(due_problems)}" if due_problems else ""
    
    print("\n" + "="*70)
    print(f"🚀 DSA TRACKER | {game.get_status_badge()}{review_msg}")
    print(f"   Progress: {solved}/{total} Solved")
    print("="*70)
    
    c.execute("SELECT id, title, filename, is_solved FROM problems")
    rows = c.fetchall()
    
    for row in rows:
        status = "[✅]" if row[3] else "[  ]"
        # Highlight due problems with a special mark
        is_due = any(p[0] == row[0] for p in due_problems)
        mark = "⚠️ " if is_due else ""
        print(f"{row[0]:<3} {status} {mark}{row[1]}")
    
    conn.close()
    print("-" * 70)
    print("Enter ID to solve  |  H for History  |  G for Graph  |  Q to Quit") # <--- UPDATE THIS LINE
    return rows

# Add this near the top of main.py
SOLUTIONS_DIR = "solutions"

# ... (keep existing code) ...

def solve_mode(problem_id):
    """The interactive mode for solving."""
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT title, instructions, filename, solution_stub, test_code, is_solved FROM problems WHERE id = ?", (problem_id,))
    data = c.fetchone()
    conn.close()
    
    if not data: return
    title, instructions, filename, stub, test_code, is_solved = data
    
    # --- PATH UPDATE ---
    # We combine the folder name with the filename
    full_path = os.path.join(SOLUTIONS_DIR, filename)
    
    print("\n" + "*"*50)
    print(f"🧠 PROBLEM: {title}")
    print("*"*50)
    print(instructions)
    print("-" * 50)
    
    if not os.path.exists(full_path):
        with open(full_path, 'w') as f:
            f.write(f"# {title}\n{stub}")
        print(f"📄 Created file: {full_path}")
    else:
        print(f"📄 Using existing file: {full_path}")

    # Mistake Log Logic (Keep as is...)
    history = db.get_problem_history(problem_id)
    failed_tries = sum(1 for h in history if not h[1])
    if failed_tries > 0:
        print(f"\n📊 History: {len(history)} attempts ({failed_tries} failures)")
        choice = input("👉 Press [H] for Mistake Log, or [ENTER] to solve: ").strip().lower()
        if choice == 'h':
            print("--- Mistake Log Shown ---") # (Simplified for brevity)

    input(f"\n⏱️  Timer will start when you press [ENTER]...")
    
    # --- START TIMER ---
    start_time = time.time()
    
    print(f"\n👉 Edit '{full_path}' now.")
    input("👉 When done, press [ENTER] to check...")
    
    # --- END TIMER ---
    end_time = time.time()
    duration = round(end_time - start_time, 2)
    
    print("\n🏃 Running Tests...")
    
    # Pass the FULL PATH to the runner now
    result = runner.run_test_module(test_code, filename) 
    
    db.log_attempt(problem_id, result['success'], result['message'], time_taken=duration)
    
    print(result['message'])
    
    if result['success']:
        print(f"\n⏱️  Time Taken: {duration} seconds")
        
        # Pass the FULL PATH to the linter
        print("\n🔍 Checking Code Quality...")
        score, feedback = qc.check_code_quality(full_path) 
        style_badge = qc.get_style_badge(score)
        print(f"   Score: {score}/10.0  ->  {style_badge}")
        
        if score < 10.0:
            print("   Tip: Improve variable names or spacing to get S Rank!")
        
        if not is_solved:
            print(game.award_xp(problem_id))
        else:
            print("💡 Problem already solved.")
            
    input("\nPress [ENTER] to return...")

def main():
    db.init_db()
    sync_html_files()
    
    while True:
        problems = show_dashboard()
        choice = input("\n> ").strip().lower()
        
        if choice == 'q': 
            print("Goodbye! Happy Coding.")
            break
        elif choice == 'h': 
            show_history_stats()
        elif choice == 'g':               # <--- ADDED THIS BLOCK
            viz.generate_progress_graph()
        else:
            try:
                pid = int(choice)
                if any(p[0] == pid for p in problems): 
                    solve_mode(pid)
                else:
                    print("⚠️  ID not found.")
            except ValueError:
                pass

if __name__ == "__main__":
    main()