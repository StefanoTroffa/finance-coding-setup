"""End-to-end tests for the finance-coding-setup hook scripts.

Validates that Layer 1 (pre_write_quality.py) and Layer 2 (post_bash_output.py)
correctly detect violations and fail open on bad input.

Run from repo root: python3 hooks/test_hooks.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
REPO_DIR = HOOKS_DIR.parent

PASS = 0
FAIL = 0


def run_hook(script, json_input):
    """Run a hook script with JSON on stdin, return (exit_code, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / script)],
        input=json.dumps(json_input),
        capture_output=True,
        text=True,
        cwd=str(REPO_DIR),
    )
    return proc.returncode, proc.stdout, proc.stderr


def test(name, passed, detail=""):
    """Record and print a test result."""
    global PASS, FAIL
    if passed:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")
        if detail:
            print(f"        {detail}")


def make_write_input(filename, content):
    """Build a Write tool_input JSON payload using a temp directory path."""
    return {"tool_input": {
        "file_path": str(Path(tempfile.gettempdir()) / filename),
        "content": content,
    }}


def make_bash_input(command):
    """Build a Bash tool_input JSON payload."""
    return {"tool_input": {"command": command}}


# ========================================
# Layer 1: pre_write_quality.py
# ========================================
print("\n=== Layer 1: pre_write_quality.py ===\n")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "clean.py", 'import os\nprint("hello")\n'))
test("Clean Python passes", code == 0, f"exit={code}, stderr={err[:100]}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "readme.md", '# Hello\napi_key = "sk-ant-FAKE1234567890abcdef"\n'))
test("Non-Python file skipped", code == 0, f"exit={code}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "secrets.py", 'api_key = "sk-ant-FAKE1234567890abcdefghijklmnop"\nprint(api_key)\n'))
test("Hardcoded secret blocks", code == 2, f"exit={code}, stderr={err[:200]}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "env_secret.py", 'import os\napi_key = os.getenv("FRED_API_KEY")\nprint(api_key)\n'))
test("getenv() secret passes", code == 0, f"exit={code}, stderr={err[:100]}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "bare_except.py", 'try:\n    x = 1\nexcept:\n    pass\n'))
test("Bare except blocks", code == 2, f"exit={code}, stderr={err[:200]}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "proper_except.py",
    'try:\n    x = 1\nexcept ValueError as e:\n    print(f"Error: {e}")\n    raise\n'))
test("Proper except passes", code == 0, f"exit={code}, stderr={err[:100]}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "no_val.py", 'import pandas as pd\ndf = pd.DataFrame()\ndf.to_excel("output.xlsx")\n'))
test("to_excel without validation blocks", code == 2, f"exit={code}, stderr={err[:200]}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "with_val.py",
    'import pandas as pd\ndf = pd.DataFrame({"a": [1]})\n'
    'if df.empty:\n    raise ValueError("no data")\n'
    'df.to_excel(output_dir + "/out.xlsx")\n'))
test("to_excel with validation passes", code == 0, f"exit={code}, stderr={err[:100]}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "bad_path.py",
    'import pandas as pd\ndf = pd.DataFrame({"a": [1]})\n'
    'if df.empty:\n    raise ValueError("x")\n'
    'df.to_excel("/home/user/data.xlsx")\n'))
test("Hardcoded output path blocks", code == 2, f"exit={code}, stderr={err[:200]}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "good_path.py",
    'import pandas as pd\ndf = pd.DataFrame({"a": [1]})\n'
    'if df.empty:\n    raise ValueError("x")\n'
    'df.to_excel("~/finance-outputs/data.xlsx")\n'))
test("finance-outputs path passes", code == 0, f"exit={code}, stderr={err[:100]}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "naive_dt.py", 'from datetime import datetime\nnow = datetime.now()\n'))
test("Naive datetime blocks", code == 2, f"exit={code}, stderr={err[:200]}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "tz_dt.py",
    'from datetime import datetime\nfrom zoneinfo import ZoneInfo\n'
    'now = datetime.now(tz=ZoneInfo("US/Eastern"))\n'))
test("TZ-aware datetime passes", code == 0, f"exit={code}, stderr={err[:100]}")

code, out, err = run_hook("pre_write_quality.py", make_write_input(
    "except_pass.py", 'try:\n    x = 1\nexcept Exception:\n    pass\n'))
test("except Exception: pass blocks", code == 2, f"exit={code}, stderr={err[:200]}")

# Fail-open tests
proc = subprocess.run(
    [sys.executable, str(HOOKS_DIR / "pre_write_quality.py")],
    input="", capture_output=True, text=True, cwd=str(REPO_DIR))
test("Empty stdin fails open", proc.returncode == 0, f"exit={proc.returncode}")

proc = subprocess.run(
    [sys.executable, str(HOOKS_DIR / "pre_write_quality.py")],
    input="not json {{{", capture_output=True, text=True, cwd=str(REPO_DIR))
test("Malformed JSON fails open", proc.returncode == 0, f"exit={proc.returncode}")


# ========================================
# Layer 2: post_bash_output.py
# ========================================
print("\n=== Layer 2: post_bash_output.py ===\n")

code, out, err = run_hook("post_bash_output.py", make_bash_input("ls -la"))
test("Non-Python command skipped", code == 0 and out.strip() == "", f"exit={code}, out={out[:100]}")

code, out, err = run_hook("post_bash_output.py", make_bash_input("python3 script.py"))
test("Python command processed (no crash)", code == 0, f"exit={code}")

code, out, err = run_hook("post_bash_output.py", make_bash_input("uv run python script.py"))
test("uv run python recognized", code == 0, f"exit={code}")

# Create a real empty CSV and test detection
tmp_csv = Path(tempfile.mktemp(suffix=".csv"))
tmp_csv.write_text("date,price,volume\n")

code, out, err = run_hook("post_bash_output.py", make_bash_input(
    f'python3 -c "print(\'done\')" "{tmp_csv}"'))
test("Empty CSV path in command", code == 0, f"exit={code}, out_len={len(out)}")
tmp_csv.unlink(missing_ok=True)

# Fail-open
proc = subprocess.run(
    [sys.executable, str(HOOKS_DIR / "post_bash_output.py")],
    input="", capture_output=True, text=True, cwd=str(REPO_DIR))
test("Empty stdin fails open", proc.returncode == 0, f"exit={proc.returncode}")


# ========================================
# Summary
# ========================================
print(f"\n{'='*40}")
print(f"Results: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
if FAIL > 0:
    print("SOME TESTS FAILED - fix before shipping")
    sys.exit(1)
else:
    print("All tests passed")
    sys.exit(0)
