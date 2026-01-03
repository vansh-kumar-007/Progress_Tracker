import database_manager as db

def calculate_xp_reward(tries_count):
    """
    Decides how much XP to give based on performance.
    - First Try: 50 XP
    - 2-5 Tries: 30 XP
    - 5+ Tries: 10 XP (At least you didn't give up!)
    """
    if tries_count <= 1:
        return 50
    elif tries_count <= 5:
        return 30
    else:
        return 10

def award_xp(problem_id):
    """
    Calculates XP, updates DB, and returns a success message.
    """
    # 1. Check how many attempts it took
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM attempts WHERE problem_id = ?", (problem_id,))
    result = c.fetchone()
    tries = result[0] if result else 1
    conn.close()
    
    # 2. Calculate Reward
    xp_amount = calculate_xp_reward(tries)
    
    # 3. Update Database
    leveled_up, new_level, total_xp = db.update_xp(xp_amount)
    
    # 4. Create message
    msg = f"\n⭐ +{xp_amount} XP EARNED! (Total: {total_xp})"
    if leveled_up:
        msg += f"\n🆙 LEVEL UP! You are now Level {new_level}!"
        
    return msg

def get_status_badge():
    """Returns a string to display on the dashboard."""
    stats = db.get_user_stats()
    if stats:
        xp, level, streak = stats
    else:
        xp, level, streak = 0, 1, 0
        
    return f"🏆 Level {level} | ✨ {xp} XP | 🔥 Streak: {streak}"