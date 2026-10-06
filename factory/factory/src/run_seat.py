#!/usr/bin/env python3
"""
run_seat.py — start one Band seat via the OpenCode adapter.

Usage:
    uv run python src/run_seat.py <seat> [model_id]
    uv run python src/run_seat.py --model-of <seat>      # print the mandate's model id

    seat      : key in agent_config.yaml  (foreman | smith | inspector | stresser)
    model_id  : optional; exact Featherless model id. If omitted, the mandate's
                "Model:" line is used. If given, it must equal the mandate's.

Env: TURN_TIMEOUT_S (default 900) = per-turn timeout passed to the adapter.

The script:
  - Loads .env and agent_config.yaml from the directory that contains this file's
    parent (i.e. <factory_root>/).
  - Reads <factory_root>/mandates/<seat>.md and verifies its "Model:" line matches
    the model_id argument exactly; exits 1 if they differ.
  - Requires RESULT_REPO env var (absolute path of the result git repository).
  - Builds OpencodeAdapter with auto_accept + auto_reject questions and runs it.
  - Never imports from "thenvoi"; always from "band".
"""

import asyncio
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate factory root: directory containing src/
# ---------------------------------------------------------------------------
FACTORY_ROOT = Path(__file__).resolve().parent.parent


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def usage() -> None:
    print(__doc__)
    sys.exit(0)


# ---------------------------------------------------------------------------
# Mandate validation
# ---------------------------------------------------------------------------
def mandates_dir() -> Path:
    """<root>/mandates, else <root>/../mandates (when this tooling is packaged as
    <repo>/factory/ next to <repo>/mandates/)."""
    for cand in (FACTORY_ROOT / "mandates", FACTORY_ROOT.parent / "mandates"):
        if cand.is_dir():
            return cand
    die(f"No mandates/ directory found next to {FACTORY_ROOT}")
    raise AssertionError  # unreachable


def read_mandate(seat: str) -> str:
    mandate_path = mandates_dir() / f"{seat}.md"
    if not mandate_path.exists():
        die(f"Mandate not found: {mandate_path}")
    return mandate_path.read_text(encoding="utf-8")


def extract_mandate_model(text: str) -> str | None:
    """Return the value on the 'Model:' line, stripped, or None."""
    for line in text.splitlines():
        m = re.match(r"^[-*_ \t]*Model[*_ \t]*:\s*(.+)$", line.strip())
        if m:
            val = m.group(1).strip().strip("*_`").strip()
            if val:
                return val
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def run(seat: str, model_id: str | None) -> None:
    from dotenv import load_dotenv

    # Load .env from factory root (never from result repo)
    load_dotenv(FACTORY_ROOT / ".env")

    result_repo = os.environ.get("RESULT_REPO", "")
    if not result_repo:
        die("RESULT_REPO environment variable is not set. Export the absolute path of the result repo.")
    result_repo_path = Path(result_repo)
    if not result_repo_path.is_dir():
        die(f"RESULT_REPO does not exist or is not a directory: {result_repo}")
    if not (result_repo_path / ".git").exists():
        die(
            f"RESULT_REPO is not a git repository (no .git found): {result_repo}\n"
            f"  Run: ./bootstrap-repo.sh {result_repo}"
        )

    # Validate mandate
    mandate_text = read_mandate(seat)
    mandate_model = extract_mandate_model(mandate_text)
    if mandate_model is None:
        die(f"Mandate {seat}.md has no 'Model:' line. Add 'Model: {model_id}' near the top.")
    if model_id is None:
        model_id = mandate_model
    if mandate_model != model_id:
        die(
            f"Model mismatch for seat '{seat}':\n"
            f"  mandate says : {mandate_model}\n"
            f"  argument says: {model_id}\n"
            f"Either fix the mandate or supply the correct model id."
        )

    # Load band config
    from band import Agent, Emit, configure_logging
    from band.adapters import OpencodeAdapter, OpencodeAdapterConfig
    from band.config import load_agent_config

    configure_logging(root_level="INFO")

    try:
        agent_id, api_key = load_agent_config(seat, config_path=FACTORY_ROOT / "agent_config.yaml")
    except Exception as exc:
        die(f"Failed to load agent config for seat '{seat}' from {FACTORY_ROOT / 'agent_config.yaml'}: {exc}")

    config = OpencodeAdapterConfig(
        base_url="http://127.0.0.1:4096",
        directory=str(result_repo_path.resolve()),
        provider_id="featherless",
        model_id=model_id,
        custom_section=mandate_text,
        approval_mode="auto_accept",
        # Never wait for a human to answer a question – auto-reject keeps the run dark.
        question_mode="auto_reject",
        turn_timeout_s=int(os.environ.get("TURN_TIMEOUT_S", "900")),
        session_title_prefix=seat,
    )

    adapter = OpencodeAdapter(
        config=config,
        emit={Emit.TOOL_CALLS, Emit.TASK_EVENTS},
    )

    agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
    print(f"[run_seat] Starting seat '{seat}' with model '{model_id}' → {result_repo}")
    await agent.run()


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        usage()
    if args[0] == "--model-of":
        if len(args) != 2:
            die("Usage: run_seat.py --model-of <seat>")
        model = extract_mandate_model(read_mandate(args[1]))
        if model is None:
            die(f"Mandate {args[1]}.md has no 'Model:' line.")
        print(model)
        return
    if len(args) not in (1, 2):
        print("Usage: run_seat.py <seat> [model_id]", file=sys.stderr)
        sys.exit(1)
    seat = args[0]
    model_id = args[1] if len(args) == 2 else None
    try:
        asyncio.run(run(seat, model_id))
    except KeyboardInterrupt:
        print(f"\n[run_seat] Seat '{seat}' stopped cleanly (SIGINT).")
        sys.exit(0)
    except Exception as exc:  # SystemExit from die() is not an Exception subclass
        import traceback

        traceback.print_exc()
        die(f"Seat '{seat}' encountered unhandled error: {exc}")


if __name__ == "__main__":
    main()
