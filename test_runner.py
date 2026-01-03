import subprocess
import sys
import os

TEST_TEMP_FILE = "evaluate_temp.py"

def run_test_module(test_code, user_filename):
    """Runs the test code against the user's specific file in the solutions folder."""
    
    # Remove .py to get module name (e.g. "Square_Pattern")
    module_name = user_filename.replace('.py', '')
    
    # CRITICAL CHANGE: We import from the 'solutions' package
    # "from exercise import..."  becomes  "from solutions.Square_Pattern import..."
    patched_code = test_code.replace("from exercise import", f"from solutions.{module_name} import")

    with open(TEST_TEMP_FILE, 'w') as f:
        f.write(patched_code)

    result = subprocess.run(
        [sys.executable, TEST_TEMP_FILE],
        capture_output=True,
        text=True
    )

    if os.path.exists(TEST_TEMP_FILE):
        os.remove(TEST_TEMP_FILE)

    is_success = (result.returncode == 0)
    
    if is_success:
        message = "✅ All tests passed!"
    else:
        message = format_error_message(result.stderr)

    return {
        "success": is_success,
        "message": message
    }

def format_error_message(raw_error):
    """Parses the messy stderr from unittest."""
    lines = raw_error.split('\n')
    clean_output = []
    
    for line in lines:
        line = line.strip()
        if line.startswith("FAIL:"):
            test_name = line.split(' ')[1]
            clean_output.append(f"\n🔻 FAILED TEST CASE: {test_name}")
        elif line.startswith("AssertionError:"):
            diff = line.replace("AssertionError: ", "")
            clean_output.append(f"   ⚠️  Mismatch: {diff}")
            
    if not clean_output:
        return "⚠️ Error details:\n" + "\n".join(lines[-5:])
        
    return "\n".join(clean_output)