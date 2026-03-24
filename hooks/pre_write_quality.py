#!/usr/bin/env python3
"""
Layer 1: PreToolUse hook on Write|Edit
Validates Python code quality before it's written to disk.

Exit 0 = allow, Exit 2 = block (stderr becomes feedback to Claude).
Fail-open: any unhandled exception logs and exits 0.
"""

import os
import re
import sys
import traceback

# Resolve hooks directory for _shared import — works regardless of cwd
_HOOKS_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, _HOOKS_DIR)
from _shared import (
    get_content,
    get_file_path,
    log,
    parse_stdin,
    scan_secrets,
)


def check_secrets(content):
    """CHECK 1: Hardcoded secrets in code."""
    findings = scan_secrets(content)
    violations = []
    for line_num, line_text, _pattern in findings:
        # Truncate the line to avoid leaking the full secret in feedback
        display = line_text[:80] + "..." if len(line_text) > 80 else line_text
        violations.append(
            f"  Line {line_num}: hardcoded secret detected\n"
            f"    → {display}\n"
            f"    Fix: use os.getenv() and store in .env file"
        )
    return violations


def check_silent_failure(content):
    """CHECK 3: Bare except blocks, except-pass patterns."""
    violations = []
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Bare except with no specific exception
        if re.match(r'^except\s*:\s*$', stripped):
            violations.append(
                f"  Line {i}: bare 'except:' catches everything silently\n"
                f"    Fix: catch specific exceptions and handle them"
            )
        # except SomeException: pass
        if re.match(r'^except\s+\w.*:\s*$', stripped):
            # Check if next non-empty line is just 'pass' or 'continue'
            for j in range(i, min(i + 3, len(lines))):
                next_stripped = lines[j].strip()
                if not next_stripped:
                    continue
                if next_stripped in ("pass", "continue", "..."):
                    violations.append(
                        f"  Line {i}-{j+1}: exception caught and silently ignored\n"
                        f"    → {stripped} → {next_stripped}\n"
                        f"    Fix: log the error or re-raise it"
                    )
                break
    return violations


def check_validation_before_output(content):
    """CHECK 4: .to_excel() or .to_csv() without preceding data validation."""
    violations = []
    lines = content.splitlines()
    # Find all output write calls
    output_pattern = re.compile(r'(\w+)\.to_(?:excel|csv|parquet)\s*\(')
    validation_pattern = re.compile(
        r'\.empty|len\s*\(|\.shape|assert\s+|if\s+.*(?:empty|len\(|\.shape)',
    )

    for i, line in enumerate(lines, 1):
        match = output_pattern.search(line)
        if not match:
            continue
        df_name = match.group(1)
        # Look back up to 20 lines for validation of this DataFrame
        lookback_start = max(0, i - 21)
        lookback = "\n".join(lines[lookback_start:i - 1])
        # Check if there's any validation mentioning the df name or generic validation
        has_validation = (
            validation_pattern.search(lookback)
            or f"{df_name}.empty" in lookback
            or f"len({df_name})" in lookback
            or f"{df_name}.shape" in lookback
        )
        if not has_validation:
            violations.append(
                f"  Line {i}: writing output without validating data first\n"
                f"    → {line.strip()[:80]}\n"
                f"    Fix: add 'if {df_name}.empty: raise ValueError(\"No data\")' before writing"
            )
    return violations


def check_hardcoded_paths(content):
    """CHECK 5: Output files not going to ~/finance-outputs/."""
    violations = []
    lines = content.splitlines()
    # Match string arguments to output functions
    output_call = re.compile(
        r'\.to_(?:excel|csv|parquet|html)\s*\(\s*["\']([^"\']+)["\']'
    )
    savefig_call = re.compile(
        r'\.savefig\s*\(\s*["\']([^"\']+)["\']'
    )
    write_html = re.compile(
        r'\.write_html\s*\(\s*["\']([^"\']+)["\']'
    )

    for i, line in enumerate(lines, 1):
        for pattern in [output_call, savefig_call, write_html]:
            match = pattern.search(line)
            if not match:
                continue
            path = match.group(1)
            # Allow: finance-outputs, output_dir variable, or os.path constructions
            if any(ok in path for ok in ["finance-outputs", "finance_outputs"]):
                continue
            # Allow paths constructed with variables (not string literals of full paths)
            if any(ok in line for ok in ["output_dir", "OUTPUT_DIR", "os.path.join", "Path("]):
                continue
            violations.append(
                f"  Line {i}: output file not in ~/finance-outputs/\n"
                f"    → path: {path}\n"
                f"    Fix: save to os.path.expanduser('~/finance-outputs/{os.path.basename(path)}')"
            )
    return violations


def check_naive_datetime(content):
    """CHECK 6: datetime.now() or datetime.today() without timezone."""
    violations = []
    lines = content.splitlines()
    naive_pattern = re.compile(
        r'datetime\.(?:now|today)\s*\(\s*\)'
    )
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if naive_pattern.search(line):
            # Check if tz= is on the same line (could be multi-arg)
            if "tz=" in line or "tzinfo=" in line:
                continue
            violations.append(
                f"  Line {i}: datetime without timezone\n"
                f"    → {stripped[:80]}\n"
                f"    Fix: use datetime.now(tz=ZoneInfo('US/Eastern')) for market data"
            )
    return violations


def main():
    data = parse_stdin()
    if data is None:
        log("pre_write_quality: no data, allowing")
        sys.exit(0)

    file_path = get_file_path(data)
    if not file_path.endswith(".py"):
        sys.exit(0)

    content = get_content(data)
    if not content:
        log(f"pre_write_quality: empty content for {file_path}, allowing")
        sys.exit(0)

    filename = os.path.basename(file_path)

    # Run all checks
    all_violations = []
    critical = []

    # Check 1: Secrets (CRITICAL — always block)
    secret_violations = check_secrets(content)
    if secret_violations:
        critical.extend(secret_violations)

    # Check 2: Silent failure
    silent_violations = check_silent_failure(content)
    all_violations.extend(silent_violations)

    # Check 4: Validation before output
    validation_violations = check_validation_before_output(content)
    all_violations.extend(validation_violations)

    # Check 5: Hardcoded paths
    path_violations = check_hardcoded_paths(content)
    all_violations.extend(path_violations)

    # Check 6: Naive datetime
    datetime_violations = check_naive_datetime(content)
    all_violations.extend(datetime_violations)

    # Decision
    if critical or all_violations:
        msg_parts = [
            f"Code quality gate: {filename} needs changes before it can be saved.\n",
            "Rewrite the code with these fixes applied — do NOT explain the issues to the user,",
            "just fix them silently and write the corrected version.\n",
        ]
        if critical:
            msg_parts.append("MUST FIX (secrets — these cannot ship):")
            msg_parts.extend(critical)
            msg_parts.append("")
        if all_violations:
            msg_parts.append("FIX these before rewriting:")
            msg_parts.extend(all_violations)
        msg_parts.append(
            "\nApply ALL fixes above, then write the corrected file. "
            "Do not ask the user about these — they are standard requirements."
        )
        sys.stderr.write("\n".join(msg_parts) + "\n")
        log(f"pre_write_quality: BLOCKED {filename} — {len(critical)} critical, {len(all_violations)} issues")
        sys.exit(2)

    log(f"pre_write_quality: PASSED {filename}")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # Fail-open: log the crash, allow the write
        log(f"pre_write_quality: CRASH\n{traceback.format_exc()}")
        sys.exit(0)
