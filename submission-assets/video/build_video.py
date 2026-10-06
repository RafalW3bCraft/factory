#!/usr/bin/env python3
"""Build the redacted Pocketful Factory presentation using FFmpeg only.

Requirements: ffmpeg with drawtext and flite filters, ffprobe, and DejaVu Sans.
Source recordings remain unchanged; their audio tracks are never mapped.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


VIDEO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = VIDEO_DIR.parents[1]
OUTPUT = VIDEO_DIR / "pocketful-factory-video.mp4"
NARRATION_OUTPUT = VIDEO_DIR / "pocketful-factory-narration.mp3"
WIDTH, HEIGHT, FPS = 1920, 1080, 30
FONT_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

ROOM_REVIEW = (
    PROJECT_ROOT
    / "attached_assets/2026-10-06_00-35-06_1791263314917.mkv"
)
ROOM_FOLLOWUP = (
    PROJECT_ROOT
    / "attached_assets/2026-10-06_00-34-17_1791263309800.mkv"
)

SCENES = [
    {
        "kind": "title",
        "eyebrow": "SUBMISSION PRESENTATION",
        "title": "Pocketful Factory",
        "subtitle": "A four-seat software factory for wallet and P2P payments",
        "metric": "4 SEATS",
        "metric_lines": ["Foreman  /  Smith", "Inspector  /  Stresser"],
        "narration": (
            "Pocketful Factory is a four-seat software factory built for a "
            "wallet and peer-to-peer payments challenge."
        ),
    },
    {
        "kind": "slide",
        "eyebrow": "THE PROBLEM",
        "title": "Correctness means more than a 200",
        "subtitle": "A payments service must protect the entire ledger.",
        "bullets": [
            "Conserve the seeded balance total",
            "Reject malformed requests explicitly",
            "Verify money flows, not just one endpoint",
        ],
        "metric": "WALLET",
        "metric_lines": ["Peer-to-peer payments", "Stage 1 API"],
        "narration": (
            "For payments, correctness means more than a successful response. "
            "Balances must conserve funds, and malformed requests must fail safely."
        ),
    },
    {
        "kind": "slide",
        "eyebrow": "HOW THE FACTORY WORKS",
        "title": "Four seats. Independent checks.",
        "subtitle": "Each role has a defined handoff and evidence trail.",
        "bullets": [
            "Foreman coordinates and routes the work",
            "Smith implements and commits revisions",
            "Inspector verifies the submitted revision",
            "Stresser probes resilience and edge cases",
        ],
        "metric": "PLAN",
        "metric_lines": ["BUILD  >  VERIFY", ">  STRESS"],
        "narration": (
            "Foreman coordinates, Smith implements, Inspector independently "
            "verifies, and Stresser probes resilience. Defects return to Smith "
            "for a verified follow-up."
        ),
    },
    {
        "kind": "room",
        "source": ROOM_REVIEW,
        "crop": "665:640:215:40",
        "source_trim": 2.0,
        "masks": [(205, 82, 460, 62), (205, 183, 460, 44), (205, 575, 460, 65)],
        "eyebrow": "REAL BAND ROOM FOOTAGE",
        "title": "Review, then harden.",
        "lines": ["Inspector accepts the revision", "Foreman routes the next probe"],
        "narration": (
            "This real Band room excerpt shows the review request, Inspector's "
            "acceptance, then a hardening order to Stresser. Workstation paths are masked."
        ),
    },
    {
        "kind": "slide",
        "eyebrow": "A DEFECT FOUND AFTER ACCEPTANCE",
        "title": "The review loop caught another gap",
        "subtitle": "Inspector accepted the first revision; Stresser raised C1 afterward.",
        "bullets": [
            "C1: empty body returned 422, not the required 400",
            "Smith fixed C1 and independently found cold-start C2",
            "Inspector later accepted the revised delta",
        ],
        "metric": "C1 + C2",
        "metric_lines": ["Stresser raised C1", "Smith self-found C2"],
        "narration": (
            "After that acceptance, Stresser flagged empty-body handling: an "
            "empty body returned 422 instead of the specified 400. Smith took the follow-up."
        ),
    },
    {
        "kind": "room",
        "source": ROOM_FOLLOWUP,
        "crop": "410:410:475:115",
        "source_start": 7.0,
        "source_trim": 1.0,
        "masks": [],
        "eyebrow": "REAL BAND ROOM FOOTAGE",
        "title": "Delta accepted; stress clean",
        "lines": ["Inspector accepts revised commit", "Stresser verdict: clean"],
        "narration": (
            "Smith fixed C1 and independently found C2. This real room excerpt "
            "shows Inspector accepting the delta and Stresser reporting a clean verdict."
        ),
    },
    {
        "kind": "slide",
        "eyebrow": "VERIFICATION",
        "title": "Results with independent evidence",
        "subtitle": "The recorded result is Stage 1, not a claim about later stages.",
        "bullets": [
            "Official harness: 147 of 147 checks passed",
            "Independent review repeated the passing result",
            "Separate private smoke suites: 145 of 145",
        ],
        "metric": "147 / 147",
        "metric_lines": ["Official harness checks", "Stage 1"],
        "narration": (
            "Stage One passed 147 of 147 official checks; independent review "
            "repeated that pass. Separate private smoke suites passed 145 of 145."
        ),
    },
    {
        "kind": "slide",
        "eyebrow": "AUTONOMY ACCOUNTING",
        "title": "The human input is part of the result",
        "subtitle": "The room log records recovery work, not just the first dispatch.",
        "bullets": [
            "4 human messages across the run",
            "3 OpenCode timeouts",
            "About 1 hour and 55 minutes stalled",
        ],
        "metric": "4 MESSAGES",
        "metric_lines": ["Dispatch  >  retry", ">  continue  >  steer"],
        "narration": (
            "The run needed four human messages, included three OpenCode "
            "timeouts, and stalled for about one hour and fifty-five minutes."
        ),
    },
    {
        "kind": "slide",
        "eyebrow": "SCOPE BOUNDARY",
        "title": "What shipped—and what did not",
        "subtitle": "The submission distinguishes verified work from unfinished scope.",
        "bullets": [
            "Stage 1 shipped",
            "Stage 2 was not committed to main",
            "Stages 3 and 4 were not reached",
        ],
        "metric": "STAGE 1",
        "metric_lines": ["Shipped and verified", "No later-stage claim"],
        "narration": (
            "Stage One shipped. Stage Two was not committed to main; Stages "
            "Three and Four were not reached. This is the verified result boundary."
        ),
    },
    {
        "kind": "slide",
        "eyebrow": "POCKETFUL FACTORY",
        "title": "Reviewable work. Visible limits.",
        "subtitle": "Real room footage • workstation paths masked • source audio muted",
        "bullets": [
            "Independent review and adversarial testing",
            "A real Stage 1 service with recorded verification",
            "Synthetic voiceover; original recordings unchanged",
        ],
        "metric": "SUBMISSION",
        "metric_lines": ["Synthetic narration", "Private paths redacted"],
        "narration": (
            "Pocketful Factory demonstrates reviewable handoffs and adversarial "
            "testing, alongside an honest account of human input and limits."
        ),
    },
]


def require_tools() -> None:
    for binary in ("ffmpeg", "ffprobe"):
        if shutil.which(binary) is None:
            raise SystemExit(f"Required executable not found: {binary}")
    if not FONT_REGULAR.is_file() or not FONT_BOLD.is_file():
        raise SystemExit("DejaVu Sans fonts not found at /usr/share/fonts/truetype/dejavu/")
    if not ROOM_REVIEW.is_file() or not ROOM_FOLLOWUP.is_file():
        raise SystemExit("The supplied real BAND room recordings are missing.")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def text_filter(
    text: str,
    x: int,
    y: int,
    size: int,
    color: str,
    directory: Path,
    index: int,
    bold: bool = False,
) -> str:
    text_path = directory / f"text-{index}.txt"
    text_path.write_text(text, encoding="utf-8")
    font = FONT_BOLD if bold else FONT_REGULAR
    return (
        f"drawtext=fontfile={font}:textfile={text_path}:expansion=none:"
        f"x={x}:y={y}:fontsize={size}:fontcolor={color}:"
        "shadowcolor=0x000000@0.6:shadowx=2:shadowy=2"
    )


def render_slide(scene: dict, image_path: Path, work_dir: Path, scene_index: int) -> None:
    filters = [
        "drawbox=x=0:y=0:w=1920:h=12:color=0x2DD4BF:t=fill",
        "drawbox=x=112:y=115:w=8:h=150:color=0x2DD4BF:t=fill",
        "drawbox=x=112:y=1000:w=1696:h=2:color=0x274156:t=fill",
        "drawbox=x=1245:y=355:w=550:h=405:color=0x111F2E:t=fill",
        "drawbox=x=1245:y=355:w=550:h=405:color=0x29475B:t=3",
    ]
    add_text = lambda text, x, y, size, color, bold=False: filters.append(
        text_filter(text, x, y, size, color, work_dir, scene_index * 40 + len(filters), bold)
    )

    if scene_index == 0:
        add_text(scene["eyebrow"], 150, 185, 26, "0x42E3CF", True)
        add_text(scene["title"], 145, 325, 84, "0xF1F5F9", True)
        add_text(scene["subtitle"], 150, 480, 33, "0xC4D3E2")
        add_text("REVIEWABLE SOFTWARE FACTORY", 150, 576, 22, "0x91A6BA", True)
    else:
        add_text(scene["eyebrow"], 150, 82, 22, "0x42E3CF", True)
        add_text(scene["title"], 150, 165, 58, "0xF1F5F9", True)
        add_text(scene["subtitle"], 152, 276, 27, "0xC4D3E2")
        for line_index, bullet in enumerate(scene["bullets"]):
            add_text(f"-  {bullet}", 170, 405 + line_index * 78, 29, "0xE3EBF3")

    add_text(scene["metric"], 1280, 430, 44, "0x42E3CF", True)
    for line_index, line in enumerate(scene["metric_lines"]):
        add_text(line, 1280, 515 + line_index * 54, 25, "0xD6E2ED")
    add_text("POCKETFUL  /  STAGE 1 SUBMISSION", 115, 1024, 17, "0x8196AA", True)
    if scene_index == len(SCENES) - 1:
        add_text("SYNTHETIC VOICEOVER  •  PATHS MASKED", 1160, 1024, 17, "0x8196AA", True)

    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x091321:s={WIDTH}x{HEIGHT}:r={FPS}",
            "-vf",
            ",".join(filters),
            "-frames:v",
            "1",
            "-update",
            "1",
            str(image_path),
        ]
    )


def room_video_filter(scene: dict, work_dir: Path, scene_index: int) -> str:
    crop = scene["crop"]
    filters = ["setpts=PTS-STARTPTS", f"crop={crop}"]
    for x, y, width, height in scene["masks"]:
        filters.append(
            f"drawbox=x={x}:y={y}:w={width}:h={height}:color=0x000000:t=fill"
        )
    filters.extend(
        [
            "scale=1040:920:force_original_aspect_ratio=decrease",
            "pad=1080:920:(ow-iw)/2:(oh-ih)/2:color=0x101A28",
            "setsar=1",
            "pad=1920:1080:80:80:color=0x091321",
            "drawbox=x=77:y=77:w=1086:h=926:color=0x29475B:t=3",
        ]
    )
    filters.append(
        text_filter(scene["eyebrow"], 1220, 245, 22, "0x42E3CF", work_dir, scene_index * 40, True)
    )
    filters.append(
        text_filter(scene["title"], 1220, 315, 38, "0xF1F5F9", work_dir, scene_index * 40 + 1, True)
    )
    for line_index, line in enumerate(scene["lines"]):
        filters.append(
            text_filter(
                line,
                1220,
                420 + line_index * 64,
                25,
                "0xD6E2ED",
                work_dir,
                scene_index * 40 + 2 + line_index,
            )
        )
    filters.append(
        text_filter(
            "PRIVATE PATHS MASKED",
            1220,
            850,
            20,
            "0x42E3CF",
            work_dir,
            scene_index * 40 + 15,
            True,
        )
    )
    filters.append(
        text_filter(
            "SOURCE AUDIO MUTED",
            1220,
            890,
            20,
            "0x91A6BA",
            work_dir,
            scene_index * 40 + 16,
        )
    )
    return ",".join(filters)


def synthesize_narration(text: str, path: Path) -> None:
    text_path = path.with_suffix(".txt")
    text_path.write_text(text, encoding="utf-8")
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"flite=textfile={text_path}:voice=kal",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(path),
        ]
    )


def render_segment(
    scene: dict,
    image_path: Path | None,
    narration_path: Path,
    duration: float,
    output_path: Path,
    scene_index: int,
    work_dir: Path,
) -> None:
    fade_out_start = max(duration - 0.42, 0.25)
    prefix = (
        room_video_filter(scene, work_dir, scene_index) + ","
        if scene["kind"] == "room"
        else ""
    )
    video_filter = (
        f"{prefix}fps={FPS},setpts=PTS-STARTPTS,"
        f"tpad=stop_mode=clone:stop_duration={duration:.3f},"
        "scale=1920:1080,setsar=1,"
        f"fade=t=in:st=0:d=0.28,fade=t=out:st={fade_out_start:.3f}:d=0.4"
    )
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if scene["kind"] == "room":
        if scene.get("source_start", 0) > 0:
            command += ["-ss", f"{scene['source_start']:.3f}"]
        command += ["-t", f"{scene['source_trim']:.3f}", "-i", str(scene["source"])]
    else:
        if image_path is None:
            raise ValueError("Slide segment is missing its rendered image.")
        command += ["-loop", "1", "-framerate", str(FPS), "-i", str(image_path)]
    command += [
        "-i",
        str(narration_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-vf",
        video_filter,
        "-af",
        f"apad=pad_dur={duration:.3f},atrim=duration={duration:.3f},"
        f"afade=t=out:st={fade_out_start:.3f}:d=0.4",
        "-t",
        f"{duration:.3f}",
        "-r",
        str(FPS),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run(command)


def main() -> None:
    require_tools()
    with tempfile.TemporaryDirectory(prefix="pocketful-video-") as tmp:
        work_dir = Path(tmp)
        segments: list[Path] = []
        narration_chunks: list[Path] = []

        for index, scene in enumerate(SCENES):
            voice_path = work_dir / f"voice-{index:02d}.wav"
            synthesize_narration(scene["narration"], voice_path)
            narration_chunks.append(voice_path)
            speech_duration = probe_duration(voice_path)
            duration = speech_duration + 1.65
            segment_path = work_dir / f"segment-{index:02d}.mp4"

            image_path = None
            if scene["kind"] != "room":
                image_path = work_dir / f"slide-{index:02d}.png"
                render_slide(scene, image_path, work_dir, index)

            render_segment(
                scene,
                image_path,
                voice_path,
                duration,
                segment_path,
                index,
                work_dir,
            )
            segments.append(segment_path)
            print(
                f"Rendered scene {index + 1}/{len(SCENES)} "
                f"({duration:.1f}s): {scene['eyebrow']}"
            )

        concat_list = work_dir / "segments.txt"
        concat_list.write_text(
            "".join(f"file '{segment.as_posix()}'\n" for segment in segments),
            encoding="utf-8",
        )
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-fflags",
                "+genpts",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-ar",
                "48000",
                "-af",
                "aresample=async=1:first_pts=0",
                "-movflags",
                "+faststart",
                str(OUTPUT),
            ]
        )
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(OUTPUT),
                "-map",
                "0:a:0",
                "-vn",
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "128k",
                str(NARRATION_OUTPUT),
            ]
        )

    metadata = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_name,codec_type,width,height",
            "-of",
            "json",
            str(OUTPUT),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    print(json.dumps(json.loads(metadata.stdout), indent=2))
    print(f"Video: {OUTPUT}")
    print(f"Narration track: {NARRATION_OUTPUT}")


if __name__ == "__main__":
    main()
