import sqlite3
import datetime
import os

# The name of the database file
DB_FILE = "dsa_tracker.db"

def get_connection():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DB_FILE)

def init_db():
    """
    Creates the necessary tables if they don't exist.
    """
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Problems Table
    c.execute('''CREATE TABLE IF NOT EXISTS problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT UNIQUE,
                    filename TEXT,
                    instructions TEXT,
                    solution_stub TEXT,
                    test_code TEXT,
                    is_solved BOOLEAN DEFAULT 0
                )''')
    
    # 2. Attempts Table (With time_taken)
    c.execute('''CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id INTEGER,
                    timestamp DATETIME,
                    is_success BOOLEAN,
                    error_message TEXT,
                    time_taken REAL DEFAULT 0.0,
                    FOREIGN KEY(problem_id) REFERENCES problems(id)
                )''')

    # --- MIGRATION CHECK (Crucial for existing databases) ---
    # We check if 'time_taken' column exists. If not, we add it.
    c.execute("PRAGMA table_info(attempts)")
    columns = [info[1] for info in c.fetchall()]
    if 'time_taken' not in columns:
        print("🔧 Updating database... Adding 'time_taken' column.")
        c.execute("ALTER TABLE attempts ADD COLUMN time_taken REAL DEFAULT 0.0")
    # --------------------------------------------------------

    # 3. User Stats Table
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_xp INTEGER DEFAULT 0,
                    current_level INTEGER DEFAULT 1,
                    streak_days INTEGER DEFAULT 0,
                    last_active_date TEXT
                )''')
    
    # Initialize user stats if empty
    c.execute("SELECT count(*) FROM user_stats")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO user_stats (total_xp, current_level, streak_days) VALUES (0, 1, 0)")

    conn.commit()
    conn.close()

def get_user_stats():
    """Returns the user's current stats (XP, Level, Streak)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT total_xp, current_level, streak_days FROM user_stats LIMIT 1")
    stats = c.fetchone()
    conn.close()
    return stats

def update_xp(amount):
    """Adds XP and checks for level up."""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT total_xp, current_level FROM user_stats LIMIT 1")
    result = c.fetchone()
    
    if not result:
        c.execute("INSERT INTO user_stats (total_xp, current_level, streak_days) VALUES (0, 1, 0)")
        xp, level = 0, 1
    else:
        xp, level = result
    
    new_xp = xp + amount
    new_level = (new_xp // 100) + 1
    
    c.execute("UPDATE user_stats SET total_xp = ?, current_level = ?", (new_xp, new_level))
    conn.commit()
    conn.close()
    
    return (new_level > level), new_level, new_xp

def upsert_problem(title, filename, instructions, solution_stub, test_code):
    """Inserts a new problem or updates it if it already exists."""
    conn = get_connection()
    c = conn.cursor()
    
    try:
        c.execute('''INSERT OR IGNORE INTO problems (title, filename, instructions, solution_stub, test_code) 
                     VALUES (?, ?, ?, ?, ?)''', 
                     (title, filename, instructions, solution_stub, test_code))
        
        c.execute('''UPDATE problems 
                     SET instructions=?, solution_stub=?, test_code=?
                     WHERE title=?''', 
                     (instructions, solution_stub, test_code, title))
        conn.commit()
    except Exception as e:
        print(f"❌ Error syncing problem '{title}': {e}")
    finally:
        conn.close()

def log_attempt(problem_id, is_success, error_message="", time_taken=0.0):
    """
    Records a user's attempt at solving a problem.
    (UPDATED to accept time_taken)
    """
    conn = get_connection()
    c = conn.cursor()
    
    timestamp = datetime.datetime.now()
    
    c.execute("INSERT INTO attempts (problem_id, timestamp, is_success, error_message, time_taken) VALUES (?, ?, ?, ?, ?)",
              (problem_id, timestamp, is_success, error_message, time_taken))
    
    if is_success:
        c.execute("UPDATE problems SET is_solved = 1 WHERE id = ?", (problem_id,))
        
    conn.commit()
    conn.close()

def get_problem_history(problem_id):
    """Fetches the full history of attempts for a specific problem."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, is_success, error_message
        FROM attempts
        WHERE problem_id = ?
        ORDER BY timestamp DESC
    """, (problem_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_global_stats():
    """Calculates the total successes and failures for every problem."""
    conn = get_connection()
    c = conn.cursor()
    
    query = '''
        SELECT 
            p.title,
            SUM(CASE WHEN a.is_success = 1 THEN 1 ELSE 0 END) as successes,
            SUM(CASE WHEN a.is_success = 0 THEN 1 ELSE 0 END) as failures,
            MAX(a.timestamp) as last_date
        FROM problems p
        LEFT JOIN attempts a ON p.id = a.problem_id
        GROUP BY p.title
        ORDER BY last_date DESC
    '''
    c.execute(query)
    rows = c.fetchall()
    conn.close()
    return rows



def get_activity_data():
    """
    Returns dates and solved counts for graphing.
    Output: ([list of dates], [list of counts])
    """
    conn = get_connection()
    c = conn.cursor()
    
    # SQLite query to group successes by Date
    # "SELECT date(timestamp), COUNT(*) ..."
    query = '''
        SELECT date(timestamp) as day, COUNT(*) as solved_count
        FROM attempts 
        WHERE is_success = 1
        GROUP BY day
        ORDER BY day ASC
    '''
    c.execute(query)
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return [], []
        
    # Separate into two lists
    dates = [row[0] for row in rows]
    counts = [row[1] for row in rows]
    
    return dates, counts


def delete_problem(problem_id):
    """Removes a problem and its history from the database."""
    conn = get_connection()
    c = conn.cursor()
    # SQLite automatically removes linked 'attempts' if we configured CASCADE, 
    # but to be safe, we manually delete attempts first.
    c.execute("DELETE FROM attempts WHERE problem_id = ?", (problem_id,))
    c.execute("DELETE FROM problems WHERE id = ?", (problem_id,))
    conn.commit()
    conn.close()



def add_notes_column():
    """Migration: Adds a 'user_notes' column to the problems table if it doesn't exist."""
    conn = get_connection()
    c = conn.cursor()
    try:
        # Try to select the column to see if it exists
        c.execute("SELECT user_notes FROM problems LIMIT 1")
    except:
        # If it fails, add the column
        print("Migrating DB: Adding user_notes column...")
        c.execute("ALTER TABLE problems ADD COLUMN user_notes TEXT DEFAULT ''")
        conn.commit()
    conn.close()

def save_problem_notes(problem_id, notes):
    """Saves user notes for a specific problem."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE problems SET user_notes = ? WHERE id = ?", (notes, problem_id))
    conn.commit()
    conn.close()


# --- FOR TESTING ONLY ---
if __name__ == "__main__":
    print("Testing Database Manager...")
    init_db()
    if os.path.exists(DB_FILE):
        print(f"✅ Success! '{DB_FILE}' was created/updated.")
    else:
        print(f"❌ Error: '{DB_FILE}' was not found.")