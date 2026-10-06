#!/usr/bin/env python3
"""run_seat.py — start one Band seat via the OpenCode adapter.

Usage:
    uv run python -m factory.run_seat <seat> [model_id]
    uv run python -m factory.run_seat --model-of <seat>      # print the mandate's model id

    seat      : key in agent_config.yaml (foreman | smith | inspector | stresser)
    model_id  : optional; exact Featherless model id. If omitted, the mandate's
                "Model:" line is used. If given, it must equal the mandate's.

Env:
    RESULT_REPO              (required): absolute path of the result git repository
    BAND_AGENT_ID            (optional): isolated agent ID for this seat (S2)
    BAND_API_KEY             (optional): isolated API key for this seat (S2)
    OPENCODE_BASE_URL        (optional): OpenCode server URL (default http://127.0.0.1:4096)
    OPENCODE_SERVER_PASSWORD (optional): auth password for OpenCode server (S5)
    TURN_TIMEOUT_S           (optional): per-turn timeout (default 900)
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
import sys
from pathlib import Path
from typing import NoReturn

from factory.env import load_env_safe

FACTORY_ROOT = Path(__file__).resolve().parent.parent.parent


def die(msg: str, code: int = 1) -> NoReturn:
    """Print error message to stderr and terminate process."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def usage() -> None:
    """Print module docstring usage."""
    print(__doc__)
    sys.exit(0)


def mandates_dir() -> Path:
    """Locate mandates directory adjacent to repository or tooling."""
    for cand in (FACTORY_ROOT / "mandates", FACTORY_ROOT.parent / "mandates"):
        if cand.is_dir():
            return cand
    die(f"No mandates/ directory found next to {FACTORY_ROOT}")


def read_mandate(seat: str) -> str:
    """Read mandate markdown content for a given seat."""
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


async def run(seat: str, model_id: str | None) -> None:
    """Execute the seat lifecycle with credential isolation and OpenCode adapter."""
    # Load .env safely from factory root if not already in environment
    load_env_safe(FACTORY_ROOT / ".env")

    result_repo = os.environ.get("RESULT_REPO", "").strip()
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
        die(f"Mandate {seat}.md has no 'Model:' line. Add 'Model: <model_id>' near the top.")
    if model_id is None:
        model_id = mandate_model
    if mandate_model != model_id:
        die(
            f"Model mismatch for seat '{seat}':\n"
            f"  mandate says : {mandate_model}\n"
            f"  argument says: {model_id}\n"
            f"Either fix the mandate or supply the correct model id."
        )

    # Load Band SDK
    from band import Agent, Emit, configure_logging
    from band.adapters import OpencodeAdapter, OpencodeAdapterConfig

    configure_logging(root_level="INFO")

    # Credential isolation (S2): use isolated per-process environment variables if available
    agent_id = os.environ.get("BAND_AGENT_ID", "").strip()
    api_key = os.environ.get("BAND_API_KEY", "").strip()

    if not (agent_id and api_key):
        from band.config import load_agent_config

        cfg_file = FACTORY_ROOT / "agent_config.yaml"
        if not cfg_file.exists():
            die(f"No credentials provided for seat '{seat}'. Set BAND_AGENT_ID & BAND_API_KEY or configure {cfg_file}")
        try:
            agent_id, api_key = load_agent_config(seat, config_path=cfg_file)
        except Exception as exc:
            die(f"Failed to load agent config for seat '{seat}' from {cfg_file}: {exc}")

    # OpenCode server auth (S5) & custom client factory
    server_password = os.environ.get("OPENCODE_SERVER_PASSWORD", "").strip()
    client_factory = None
    if server_password:
        from band.integrations.opencode import HttpOpencodeClient

        def auth_client_factory(cfg: OpencodeAdapterConfig) -> HttpOpencodeClient:
            client = HttpOpencodeClient(
                base_url=cfg.base_url,
                directory=cfg.directory,
                workspace=cfg.workspace,
                timeout_s=cfg.turn_timeout_s,
            )
            token = base64.b64encode(f"opencode:{server_password}".encode()).decode()
            client._client.headers["Authorization"] = f"Basic {token}"
            return client

        client_factory = auth_client_factory

    base_url = os.environ.get("OPENCODE_BASE_URL", "http://127.0.0.1:4096")
    turn_timeout_s = int(os.environ.get("TURN_TIMEOUT_S", "900"))

    config = OpencodeAdapterConfig(
        base_url=base_url,
        directory=str(result_repo_path.resolve()),
        provider_id="featherless",
        model_id=model_id,
        custom_section=mandate_text,
        approval_mode="auto_accept",
        question_mode="auto_reject",
        turn_timeout_s=turn_timeout_s,
        session_title_prefix=seat,
    )

    adapter = OpencodeAdapter(
        config=config,
        emit={Emit.TOOL_CALLS, Emit.TASK_EVENTS},
        client_factory=client_factory,
    )

    agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
    print(f"[run_seat] Starting seat '{seat}' with model '{model_id}' → {result_repo}")
    await agent.run()


def main() -> None:
    """CLI entrypoint."""
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
    except Exception as exc:
        import traceback

        traceback.print_exc()
        die(f"Seat '{seat}' encountered unhandled error: {exc}")


if __name__ == "__main__":
    main()
