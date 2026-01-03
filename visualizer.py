import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import database_manager as db
import os
import subprocess

def generate_progress_graph():
    """
    Generates a professional 'Combo Chart' (Bar + Line) with a Stats Dashboard.
    """
    # 1. Fetch Data
    raw_dates, daily_counts = db.get_activity_data()
    stats = db.get_user_stats()
    
    # Handle empty data case
    if not raw_dates:
        print("⚠️ Not enough data to generate a graph yet. Solve 1 problem first!")
        return

    # 2. Data Processing
    # Convert string dates (YYYY-MM-DD) to Python Date objects for better sorting/plotting
    dates = [datetime.strptime(d, "%Y-%m-%d") for d in raw_dates]
    
    # Calculate Cumulative Sum (Running Total)
    cumulative_counts = []
    total = 0
    for count in daily_counts:
        total += count
        cumulative_counts.append(total)

    # Unpack User Stats (Handle potential None)
    if stats:
        xp, level, streak = stats
    else:
        xp, level, streak = 0, 1, 0

    # 3. Setup the Plot Style
    plt.style.use('bmh')  # 'bmh' is a clean, professional aesthetic
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # --- LAYER 1: Daily Activity (Bars) ---
    color = 'tab:blue'
    ax1.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Daily Solved', color=color, fontsize=12, fontweight='bold')
    bars = ax1.bar(dates, daily_counts, color=color, alpha=0.6, label='Daily Activity', width=0.6)
    ax1.tick_params(axis='y', labelcolor=color)
    
    # Force integer ticks on Y-axis (no 1.5 problems)
    ax1.set_yticks(range(0, max(daily_counts) + 2))

    # --- LAYER 2: Cumulative Progress (Line) ---
    ax2 = ax1.twinx()  # Create a second Y-axis sharing the same X-axis
    color = 'tab:red'
    ax2.set_ylabel('Total Solved (Growth)', color=color, fontsize=12, fontweight='bold')
    ax2.plot(dates, cumulative_counts, color=color, marker='o', linewidth=3, label='Growth Trend')
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Fill under the line for a nice effect
    ax2.fill_between(dates, cumulative_counts, color=color, alpha=0.1)

    # --- LAYER 3: The "Heads-Up Display" (Stats Box) ---
    # We place a text box in the top-left corner
    stats_text = (
        f"🏆 LEVEL:  {level}\n"
        f"✨ XP:     {xp}\n"
        f"🔥 STREAK: {streak} Days\n"
        f"∑  TOTAL:  {total} Solved"
    )
    
    props = dict(boxstyle='round,pad=0.8', facecolor='white', alpha=0.9, edgecolor='gray')
    ax1.text(0.02, 0.95, stats_text, transform=ax1.transAxes, fontsize=12,
             verticalalignment='top', bbox=props, fontfamily='monospace')

    # 4. Formatting
    plt.title(f"DSA Mastery Progress Report", fontsize=16, fontweight='bold', pad=20)
    
    # Format X-axis dates nicely (e.g., "Jan 04")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    fig.tight_layout()  # Adjust layout to prevent clipping

    # 5. Save and Open
    output_file = "progress_report.png"
    plt.savefig(output_file, dpi=100)
    print(f"\n📊 Professional Graph saved as '{output_file}'")
    
    try:
        if os.name == 'posix':
            subprocess.run(['xdg-open', output_file], check=False)
        else:
            os.startfile(output_file)
    except Exception:
        print(f"👉 Open '{output_file}' manually to see your graph.")

    plt.close()