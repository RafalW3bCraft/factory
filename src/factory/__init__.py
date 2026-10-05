def main() -> None:
    """Entry point stub — not used at runtime.

    The factory tooling runs via shell scripts (start-factory.sh, stop-factory.sh,
    preflight.sh, bootstrap-repo.sh) and src/run_seat.py directly.
    This pyproject.toml script entry exists so 'uv run factory' works as a
    quick smoke test that the package installs correctly.
    """
    print("Factory tooling OK. Use start-factory.sh to start a run.")
