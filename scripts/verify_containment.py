"""Run actual local container boundary probes; never a native-provider clearance."""

from __future__ import annotations

import argparse
import json
import socket
import tempfile
import uuid
from pathlib import Path

from factory.verification import cleanup_command, container_command, engine_environment, run_bounded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", required=True)
    parser.add_argument("--image", required=True, help="immutable sha256: image ID already present locally")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="factoryops-containment-") as directory, socket.socket() as listener:
        root = Path(directory)
        candidate = root / "candidate"
        candidate.mkdir()
        sentinel = root / "host-only-sentinel"
        sentinel.write_text("disposable test data")
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        probe = """import os,json,socket
from pathlib import Path
assert os.geteuid()!=0
assert not Path('/var/run/docker.sock').exists()
try:
    Path('/root/.codex/auth.json').read_bytes()
except (FileNotFoundError, PermissionError):
    pass
else:
    raise AssertionError('unexpected provider credential access')
assert not Path(SENTINEL).exists()
for filename in ('/candidate/write-probe','/etc/write-probe'):
    try:
        Path(filename).write_text('denied')
    except OSError:
        pass
    else:
        raise AssertionError('read-only boundary failed')
assert set(os.listdir('/sys/class/net')) <= {'lo'}
client=socket.socket(); client.settimeout(1)
try:
    client.connect(('127.0.0.1',PORT))
except OSError:
    pass
else:
    raise AssertionError('container reached host loopback service')
finally:
    client.close()
status=Path('/proc/self/status').read_text()
assert 'CapEff:\\t0000000000000000' in status
assert 'NoNewPrivs:\\t1' in status
memory=Path('/sys/fs/cgroup/memory.max').read_text().strip()
pids=Path('/sys/fs/cgroup/pids.max').read_text().strip()
assert memory.isdigit() and int(memory)<=268435456
assert pids.isdigit() and int(pids)<=64
assert not any(x in os.environ for x in ('OPENAI_API_KEY','BAND_API_KEY','CODEX_HOME'))
print(json.dumps({'nonroot':True,'readonly':True,'host_sentinel_denied':True,'host_loopback_denied':True,'capabilities_dropped':True,'no_new_privileges':True,'memory_max':memory,'pids_max':pids,'credential_environment_absent':True}))
""".replace("SENTINEL", repr(str(sentinel))).replace("PORT", str(port))
        results = []
        for command, timeout, expected in (
            (["python", "-B", "-c", probe], 20, 0),
            (["python", "-B", "-c", "import time; time.sleep(30)"], 1, 124),
            (["python", "-B", "-c", "print('x'*1000000)"], 10, 124),
        ):
            name = "factoryops-probe-" + uuid.uuid4().hex
            try:

                def remove_container() -> None:
                    run_bounded(cleanup_command(args.engine, name), timeout=10, environment=engine_environment())

                result = run_bounded(
                    container_command(args.engine, args.image, candidate, name, command),
                    timeout=timeout,
                    environment=engine_environment(),
                    on_limit=remove_container,
                )
            finally:
                cleanup = run_bounded(cleanup_command(args.engine, name), timeout=10, environment=engine_environment())
            # Outputs are bounded, disposable-fixture data. Do not print the noisy payload.
            results.append(
                {
                    "exit_code": result["exit_code"],
                    "expected_exit_code": expected,
                    "output": result["output"] if expected == 0 else "[bounded probe output withheld]",
                    "limited": result["limited"],
                    "cleanup_exit_code": cleanup["exit_code"],
                    "container_name": name,
                }
            )
            if result["exit_code"] != expected or cleanup["limited"]:
                break
        passed = len(results) == 3 and all(x["exit_code"] == x["expected_exit_code"] for x in results)
        print(
            json.dumps(
                {
                    "engine": args.engine,
                    "image": args.image,
                    "passed": passed,
                    "native_provider_clearance": False,
                    "results": results,
                },
                indent=2,
            )
        )
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
