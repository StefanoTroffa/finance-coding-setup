"""
Shared utilities for finance-coding-setup hooks.
JSON parsing, secret detection patterns, logging.
"""

import json
import os
import re
import sys
from datetime import datetime

LOG_FILE = os.path.expanduser("~/.finance-hooks.log")


def log(msg):
    """Append timestamped message to the hook log file."""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass  # Logging must never crash the hook


def parse_stdin():
    """Read and parse JSON from stdin. Returns dict or None on failure."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            log("parse_stdin: empty stdin")
            return None
        return json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        log(f"parse_stdin: failed to parse JSON: {e}")
        return None


def get_file_path(data):
    """Extract tool_input.file_path from hook data."""
    try:
        return data.get("tool_input", {}).get("file_path", "")
    except (AttributeError, TypeError):
        return ""


def get_content(data):
    """Extract file content from Write (content) or Edit (new_string) tool input."""
    try:
        ti = data.get("tool_input", {})
        return ti.get("content", ti.get("new_string", ""))
    except (AttributeError, TypeError):
        return ""


def get_command(data):
    """Extract command string from Bash tool input."""
    try:
        return data.get("tool_input", {}).get("command", "")
    except (AttributeError, TypeError):
        return ""


# --- Secret detection ---

# Patterns that match hardcoded secrets (not env var references)
SECRET_PATTERNS = [
    # Anthropic API keys
    re.compile(r'(?:sk-ant-|sk-)[a-zA-Z0-9_-]{20,}'),
    # AWS access keys
    re.compile(r'AKIA[0-9A-Z]{16}'),
    # GitHub PATs
    re.compile(r'ghp_[a-zA-Z0-9]{36}'),
    # Generic hardcoded credentials: key = "value" (8+ chars)
    re.compile(
        r'(?:password|token|api_key|apikey|secret|api_secret|access_key)'
        r'\s*=\s*["\'][^"\']{8,}["\']',
        re.IGNORECASE,
    ),
]

# Line-level indicators that the value comes from environment (not hardcoded)
ENV_REF_PATTERNS = re.compile(
    r'os\.getenv|os\.environ|dotenv|load_dotenv|getenv|environ\.get|'
    r'os\.environ\.get|config\[|Config\(|settings\.',
    re.IGNORECASE,
)


def is_env_ref(line):
    """Returns True if the line loads the value from environment/config, not hardcoded."""
    return bool(ENV_REF_PATTERNS.search(line))


def scan_secrets(content):
    """
    Scan content for hardcoded secrets.
    Returns list of (line_number, line_text, pattern_description) tuples.
    """
    findings = []
    for i, line in enumerate(content.splitlines(), 1):
        # Skip lines that reference environment variables
        if is_env_ref(line):
            continue
        # Skip comments
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append((i, stripped, pattern.pattern[:40]))
                break  # One finding per line is enough
    return findings
