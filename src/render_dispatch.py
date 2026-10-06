#!/usr/bin/env python3
"""
render_dispatch.py — Render a dispatch template into the exact message to paste
into the lead seat's room (@Foreman).

Usage:
    python src/render_dispatch.py <template> [--task "Task summary"] [--target-env "Local / Docker"]

Supported templates:
    engineering | software-engineering
    security    | security-audit
    forensics   | forensics-crash
    Or any path to a *.md or *.md.tmpl file.

Variables (resolved from environment, arguments, or .env):
    RESULT_REPO      (required; path to target git repo)
    TASK_DESCRIPTION (optional; default: "Full-stack development and security hardening")
    TARGET_ENV       (optional; default: "Local Linux sandbox")
    WORK_ROOT        (default: parent directory of factory)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

FACTORY_ROOT = Path(__file__).resolve().parent.parent
DISPATCH_DIR = FACTORY_ROOT / "dispatch"

TEMPLATE_ALIASES = {
    "engineering": "software-engineering.md.tmpl",
    "software-engineering": "software-engineering.md.tmpl",
    "security": "security-audit.md.tmpl",
    "security-audit": "security-audit.md.tmpl",
    "forensics": "forensics-crash.md.tmpl",
    "forensics-crash": "forensics-crash.md.tmpl",
}


def load_env() -> None:
    env_file = FACTORY_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^(?:export\s+)?([A-Za-z_]\w*)\s*=\s*(.*)$", line)
            if m and m.group(1) not in os.environ:
                val = m.group(2).strip().strip("'\"")
                os.environ[m.group(1)] = val


def resolve_template_path(name_or_path: str) -> Path:
    # 1. Alias lookup
    if name_or_path in TEMPLATE_ALIASES:
        return DISPATCH_DIR / TEMPLATE_ALIASES[name_or_path]

    # 2. Check directly in dispatch/
    direct = DISPATCH_DIR / name_or_path
    if direct.is_file():
        return direct
    if (DISPATCH_DIR / f"{name_or_path}.md.tmpl").is_file():
        return DISPATCH_DIR / f"{name_or_path}.md.tmpl"

    # 3. Direct path
    custom = Path(name_or_path).resolve()
    if custom.is_file():
        return custom

    raise FileNotFoundError(f"Template not found: {name_or_path}. Available: {list(TEMPLATE_ALIASES.keys())}")


def render(template_path: Path, replacements: dict[str, str]) -> str:
    content = template_path.read_text(encoding="utf-8")
    for key, val in replacements.items():
        content = content.replace("{{" + key + "}}", val)

    # Check for unresolved tokens
    unresolved = sorted(set(re.findall(r"\{\{([A-Za-z0-9_]+)\}\}", content)))
    if unresolved:
        raise ValueError(f"Unresolved template tokens: {unresolved}")

    # Normalize excessive newlines
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Foreman dispatch template")
    parser.add_argument("template", help="Template name (engineering, security, forensics) or file path")
    parser.add_argument("--task", default="", help="Task or mission description")
    parser.add_argument("--target-env", default="", help="Target runtime environment")
    parser.add_argument("--repo", default="", help="Override RESULT_REPO path")

    args = parser.parse_args()

    load_env()

    result_repo = args.repo or os.environ.get("RESULT_REPO", "")
    if not result_repo:
        print("ERROR: RESULT_REPO must be provided via --repo, environment, or .env", file=sys.stderr)
        return 1

    work_root = os.environ.get("WORK_ROOT") or str(FACTORY_ROOT.parent)
    task_desc = args.task or os.environ.get("TASK_DESCRIPTION") or "Design, implement, test, and defensively audit project code"
    target_env = args.target_env or os.environ.get("TARGET_ENV") or "Local development sandbox / Linux environment"

    replacements = {
        "RESULT_REPO": str(Path(result_repo).resolve()),
        "WORK_ROOT": str(Path(work_root).resolve()),
        "TASK_DESCRIPTION": task_desc,
        "TARGET_ENV": target_env,
    }

    try:
        tmpl_file = resolve_template_path(args.template)
        output = render(tmpl_file, replacements)
        sys.stdout.write(output)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
