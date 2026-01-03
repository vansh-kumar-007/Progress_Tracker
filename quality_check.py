import sys
from io import StringIO
from pylint.lint import Run
from pylint.reporters.text import TextReporter
import os

def check_code_quality(filepath):
    """
    Runs Pylint on the given file path.
    """
    # Check if file exists before linting
    if not os.path.exists(filepath):
        return 0.0, "File not found."

    pylint_output = StringIO()
    reporter = TextReporter(pylint_output)
    
    try:
        # We disable some strict checks (C0114=missing module docstring)
        args = [filepath, "--disable=C0114,C0115,C0116", "--output-format=text"]
        
        result = Run(args, reporter=reporter, exit=False)
        
        score = result.linter.stats.global_note
        output_text = pylint_output.getvalue()
        
        return score, output_text
        
    except Exception as e:
        return 0.0, f"Could not run linter: {e}"

def get_style_badge(score):
    if score >= 9.0: return "🌟 Clean Code (S Rank)"
    if score >= 7.0: return "✅ Good Style (A Rank)"
    if score >= 5.0: return "⚠️ Needs Polish (B Rank)"
    return "💩 Messy (C Rank)"