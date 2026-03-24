#!/usr/bin/env python3
"""
Layer 2: PostToolUse hook on Bash
Validates Python script output after execution.

Cannot block (PostToolUse). Sends feedback to Claude via systemMessage JSON
so it can fix issues before presenting results to the user.

Fail-open: any unhandled exception logs and exits 0 silently.
"""

import json
import os
import re
import sys
import traceback
from datetime import datetime, timedelta

# Resolve hooks directory for _shared import — works regardless of cwd
_HOOKS_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, _HOOKS_DIR)
from _shared import log, parse_stdin, get_command


def find_output_files(command, tool_output=""):
    """
    Detect output file paths from the command string and stdout.
    Returns list of absolute file paths.
    """
    files = []

    # Pattern 1: String literal paths in the command with known extensions
    path_pattern = re.compile(r'["\']([^"\']*\.(?:xlsx|csv|parquet|html|png|pdf|json))["\']')
    for match in path_pattern.finditer(command):
        files.append(match.group(1))

    # Pattern 2: Scan stdout for "Saved to ...", "Output: ...", "Written to ..."
    saved_pattern = re.compile(
        r'(?:saved?\s+to|output(?:\s+file)?:|written?\s+to|created|exported\s+to)\s*:?\s*(.+\.(?:xlsx|csv|parquet|html|png|pdf|json))',
        re.IGNORECASE,
    )
    for match in saved_pattern.finditer(tool_output):
        files.append(match.group(1).strip().strip("'\""))

    # Expand ~ and resolve relative paths
    resolved = []
    for f in files:
        expanded = os.path.expanduser(f)
        if not os.path.isabs(expanded):
            # Try common locations
            for base in [os.getcwd(), os.path.expanduser("~/finance-outputs")]:
                candidate = os.path.join(base, expanded)
                if os.path.exists(candidate):
                    expanded = candidate
                    break
        resolved.append(expanded)

    return list(set(resolved))


def check_data_quality(file_path, command=""):
    """
    Inspect a CSV or XLSX file for data quality issues.
    Returns list of (severity, message) tuples.
    command: the original bash command, used to detect intentional historical pulls.
    """
    issues = []

    try:
        import pandas as pd
    except ImportError:
        log("post_bash_output: pandas not available, skipping data quality check")
        return issues

    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path, nrows=5000)
        elif file_path.endswith(".xlsx"):
            df = pd.read_excel(file_path, nrows=5000)
        elif file_path.endswith(".parquet"):
            df = pd.read_parquet(file_path)
        else:
            return issues
    except Exception as e:
        issues.append(("ERROR", f"Cannot read {os.path.basename(file_path)}: {e}"))
        return issues

    filename = os.path.basename(file_path)

    # Check 1: Empty DataFrame
    if len(df) == 0:
        issues.append(("ERROR", f"{filename} is empty (0 rows)"))
        return issues  # No point checking further

    # Check 2: NaN ratio per column
    for col in df.columns:
        nan_count = df[col].isna().sum()
        total = len(df)
        if total == 0:
            continue
        ratio = nan_count / total
        if ratio > 0.5:
            issues.append(("ERROR", f"Column '{col}' is {ratio:.0%} NaN — likely a data pull failure"))
        elif ratio > 0.1:
            issues.append(("WARNING", f"Column '{col}' has {ratio:.0%} missing values"))

    # Check 3: Date columns should be datetime, not strings
    date_cols = [c for c in df.columns if any(d in c.lower() for d in ["date", "timestamp", "time", "dt"])]
    for col in date_cols:
        if df[col].dtype == "object":
            # Try parsing to see if they're parseable dates stored as strings
            try:
                pd.to_datetime(df[col].dropna().head(10))
                issues.append(("WARNING", f"Column '{col}' contains dates stored as strings — should be datetime type"))
            except (ValueError, TypeError):
                issues.append(("ERROR", f"Column '{col}' looks like a date column but contains non-date values"))

    # Check 4: Impossible values in price-like columns
    price_cols = [c for c in df.columns if any(p in c.lower() for p in [
        "price", "close", "open", "high", "low", "adj", "bid", "ask", "mid", "nav", "vwap"
    ])]
    for col in price_cols:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        numeric = df[col].dropna()
        if len(numeric) == 0:
            continue
        neg_count = (numeric < 0).sum()
        if neg_count > 0:
            issues.append(("ERROR", f"Column '{col}' has {neg_count} negative values — prices should be positive"))
        # Extreme outlier check: values > 10x median (likely bad data)
        median = numeric.median()
        if median > 0:
            extreme = (numeric > median * 10).sum()
            if extreme > 0:
                issues.append(("WARNING", f"Column '{col}' has {extreme} values >10x the median — possible bad data"))

    # Check 5: Stale data — only if the script looks like it's pulling current/recent data
    # Skip this check if the command contains explicit historical date ranges
    looks_historical = bool(re.search(
        r'(?:19|20)\d{2}[-/]|start.*(?:19|20)\d{2}|period.*(?:max|5y|10y)|year.*(?:19|20)\d{2}|historical',
        command, re.IGNORECASE,
    ))
    if not looks_historical:
        for col in date_cols:
            try:
                dates = pd.to_datetime(df[col].dropna())
                if len(dates) == 0:
                    continue
                max_date = dates.max()
                today = datetime.now()
                if max_date.tzinfo:
                    today = datetime.now(tz=max_date.tzinfo)
                # Count business days (rough: skip weekends)
                bdays = 0
                current = max_date
                while current < today:
                    current += timedelta(days=1)
                    if current.weekday() < 5:
                        bdays += 1
                if bdays > 3:
                    issues.append((
                        "WARNING",
                        f"Most recent date in '{col}' is {max_date.strftime('%Y-%m-%d')} "
                        f"({bdays} business days ago) — data may be stale"
                    ))
            except (ValueError, TypeError):
                continue

    # Check 6: Duplicate dates (common data quality issue)
    for col in date_cols:
        try:
            dates = pd.to_datetime(df[col].dropna())
            dup_count = dates.duplicated().sum()
            if dup_count > 0:
                issues.append(("WARNING", f"Column '{col}' has {dup_count} duplicate dates"))
        except (ValueError, TypeError):
            continue

    return issues


def main():
    data = parse_stdin()
    if data is None:
        sys.exit(0)

    command = get_command(data)
    if not command:
        sys.exit(0)

    # Only process Python execution commands (python, python3, uv run python)
    if not re.search(r'(?:\bpython3?\b|uv\s+run\s+python)', command):
        sys.exit(0)

    # Get tool output (stdout/stderr from the command)
    tool_output = ""
    try:
        result = data.get("tool_result", data.get("tool_output", {}))
        if isinstance(result, dict):
            tool_output = result.get("stdout", "") + "\n" + result.get("stderr", "")
        elif isinstance(result, str):
            tool_output = result
    except (AttributeError, TypeError):
        pass

    messages = []

    # Check 1: Did the script crash?
    stderr = ""
    try:
        result = data.get("tool_result", data.get("tool_output", {}))
        if isinstance(result, dict):
            stderr = result.get("stderr", "")
    except (AttributeError, TypeError):
        pass

    if "Traceback" in stderr or "Error" in stderr:
        messages.append(
            f"The script crashed. Here's the error:\n{stderr[:500]}\n\n"
            "Fix the script and re-run it. Do not show the traceback to the user — "
            "just say something like 'Let me fix that' and run the corrected version."
        )

    # Check 2: Find and inspect output files
    output_files = find_output_files(command, tool_output)

    for file_path in output_files:
        if not os.path.exists(file_path):
            messages.append(f"Expected output file not found: {file_path}\nThe script may have failed silently.")
            continue

        # Check 3-6: Data quality inspection
        quality_issues = check_data_quality(file_path, command)
        if quality_issues:
            file_msg = f"Data quality check for {os.path.basename(file_path)}:"
            for severity, msg in quality_issues:
                file_msg += f"\n  [{severity}] {msg}"
            messages.append(file_msg)

    # If no output files found but command looks like it should produce one,
    # check ~/finance-outputs/ for recently created files
    if not output_files:
        output_dir = os.path.expanduser("~/finance-outputs")
        if os.path.isdir(output_dir):
            now = datetime.now().timestamp()
            for fname in os.listdir(output_dir):
                fpath = os.path.join(output_dir, fname)
                if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) < 60:
                    quality_issues = check_data_quality(fpath)
                    if quality_issues:
                        file_msg = f"Data quality check for {fname} (recently created):"
                        for severity, msg in quality_issues:
                            file_msg += f"\n  [{severity}] {msg}"
                        messages.append(file_msg)

    # Send feedback to Claude
    if messages:
        has_errors = any("[ERROR]" in m for m in messages)
        combined = "\n\n".join(messages)
        if has_errors:
            combined += (
                "\n\nThese data quality issues need attention before showing results. "
                "Fix the script to address ERROR items (empty data, broken columns, negative prices). "
                "For WARNINGs, mention them briefly to the user — e.g., 'Note: some values are missing in column X' — "
                "so they know the data isn't perfect, but don't make it sound alarming."
            )
        else:
            combined += (
                "\n\nThese are minor data quality notes. Mention them briefly when presenting results — "
                "e.g., 'The data goes up to March 19th' or 'A few values are missing in column X'. "
                "Don't make it sound like something is broken."
            )
        print(json.dumps({"systemMessage": combined}))
        log(f"post_bash_output: {len(messages)} issues found")
    else:
        log("post_bash_output: no issues")

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # Fail-open: log the crash, exit silently
        log(f"post_bash_output: CRASH\n{traceback.format_exc()}")
        sys.exit(0)
