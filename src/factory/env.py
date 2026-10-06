"""Safe environment file (.env) parser without shell evaluation (Finding S3).

Parses standard KEY=VALUE files strictly as data, preventing arbitrary code
execution vulnerabilities inherent in 'source .env'.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_ENV_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def parse_env_content(content: str) -> dict[str, str]:
    """Parse environment variables from a string content safely."""
    env_vars: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip().rstrip("\r")
        if not line or line.startswith("#"):
            continue
        # Remove export prefix if present
        if line.startswith("export "):
            line = line[7:].strip()
        match = _ENV_LINE_RE.match(line)
        if not match:
            continue

        key, val = match.group(1), match.group(2).strip()

        # Handle double-quoted values: "..." possibly followed by comment
        if val.startswith('"'):
            match_quoted = re.match(r'^"((?:\\.|[^"\\])*)"(?:\s*#.*)?$', val)
            if match_quoted:
                val = match_quoted.group(1)
                val = val.replace(r"\"", '"').replace(r"\n", "\n").replace(r"\t", "\t").replace(r"\\", "\\")
            elif " #" in val:
                val = val.split(" #", 1)[0].rstrip()
        # Handle single-quoted values: '...' (literal)
        elif val.startswith("'"):
            match_quoted = re.match(r"^'([^']*)'(?:\s*#.*)?$", val)
            if match_quoted:
                val = match_quoted.group(1)
            elif " #" in val:
                val = val.split(" #", 1)[0].rstrip()
        else:
            # Unquoted: strip trailing comment if preceded by whitespace
            if " #" in val:
                val = val.split(" #", 1)[0].rstrip()
            elif "\t#" in val:
                val = val.split("\t#", 1)[0].rstrip()

        env_vars[key] = val
    return env_vars


def parse_env_file(file_path: str | Path) -> dict[str, str]:
    """Read and parse environment variables safely from file path."""
    path = Path(file_path)
    if not path.is_file():
        return {}
    content = path.read_text(encoding="utf-8")
    return parse_env_content(content)


def load_env_safe(file_path: str | Path = ".env", override: bool = False) -> dict[str, str]:
    """Load variables from .env into os.environ safely without shell execution."""
    vars_dict = parse_env_file(file_path)
    for k, v in vars_dict.items():
        if override or k not in os.environ:
            os.environ[k] = v
    return vars_dict
