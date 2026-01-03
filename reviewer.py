import database_manager as db
from datetime import datetime, timedelta

def get_due_problems():
    """
    Returns a list of problems that need review.
    Logic: Solved > 3 days ago OR Failed recently.
    """
    conn = db.get_connection()
    c = conn.cursor()
    
    # Simple algorithm: Find problems solved more than 3 days ago
    review_threshold = datetime.now() - timedelta(days=3)
    
    query = '''
        SELECT p.id, p.title, MAX(a.timestamp) as last_attempt
        FROM problems p
        JOIN attempts a ON p.id = a.problem_id
        WHERE p.is_solved = 1
        GROUP BY p.id
        HAVING last_attempt < ?
    '''
    
    c.execute(query, (review_threshold,))
    rows = c.fetchall()
    conn.close()
    
    return rows