"""Record one operator-selected X11 window; start only after credential setup.

A recording is a capture artifact, not proof that a workflow passed. Review it
for secrets and real acceptance evidence before publishing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path


def recorder() -> str:
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    tooling = Path.home() / ".local/share/factoryops/tools/bin/python"
    result = subprocess.run(
        [str(tooling), "-c", "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0 or not Path(result.stdout.strip()).is_file():
        raise ValueError("Recording tool is unavailable; finish the isolated imageio-ffmpeg installation first.")
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", required=True, help="explicit X11 window ID from xwininfo")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--fps", type=int, default=5)
    args = parser.parse_args()
    if not re.fullmatch(r"0x[0-9a-fA-F]+", args.window) or not 1 <= args.seconds <= 600 or not 1 <= args.fps <= 15:
        parser.error("Use an explicit hexadecimal window ID, 1–600 seconds and 1–15 fps.")
    if (
        not args.output.is_absolute()
        or args.output.exists()
        or args.output.is_symlink()
        or not args.output.parent.is_dir()
    ):
        parser.error("Output must be a new absolute path in an existing directory.")
    if not os.environ.get("DISPLAY") or not shutil.which("import"):
        parser.error("X11 DISPLAY and ImageMagick import are required; Wayland is not supported by this recorder.")
    previous_umask = os.umask(0o077)
    started = time.monotonic()
    frames = 0
    try:
        command = [
            recorder(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-n",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-framerate",
            str(args.fps),
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-vf",
            "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-movflags",
            "+faststart",
            str(args.output),
        ]
        with args.output.with_suffix(".recording.log").open("xb") as log:
            process = subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log, start_new_session=True
            )
            try:
                assert process.stdin is not None
                try:
                    while time.monotonic() - started < args.seconds:
                        frame = subprocess.run(
                            ["import", "-window", args.window, "png:-"], capture_output=True, timeout=10, check=False
                        )
                        if frame.returncode != 0:
                            raise ValueError("Window capture failed; check the selected visible window.")
                        process.stdin.write(frame.stdout)
                        frames += 1
                        time.sleep(max(0, started + frames / args.fps - time.monotonic()))
                except KeyboardInterrupt:
                    pass
                process.stdin.close()
                code = process.wait(timeout=30)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
            if code != 0 or not frames:
                raise ValueError("Encoding failed; inspect the private recording log.")
        metadata = {
            "window": args.window,
            "frames": frames,
            "fps": args.fps,
            "wall_seconds": round(time.monotonic() - started, 2),
            "encoded_seconds": frames / args.fps,
            "audio": False,
            "workflow_verified": False,
            "review_before_publication": True,
        }
        args.output.with_suffix(".recording.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps(metadata))
    except (OSError, ValueError, subprocess.SubprocessError):
        print("Recording failed; retain private partial output/logs and correct setup before retrying.")
        return 1
    finally:
        os.umask(previous_umask)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
