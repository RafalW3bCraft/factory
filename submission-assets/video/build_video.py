#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess
import shutil

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / 'frames'
MP4_OUT = ROOT / 'pocketful-factory-video.mp4'

OUT_DIR.mkdir(exist_ok=True)

slides = [
    {
        'title': 'Pocketful Factory',
        'subtitle': 'A four-seat dark factory that proves its own work',
        'bullets': ['Track: pocketful', 'Hackathon: WeAreDevelopers x BAND', 'Evidence-driven output package'],
    },
    {
        'title': 'The problem',
        'subtitle': 'Wallet + P2P payments with protected funds',
        'bullets': ['Conservation of funds is critical', 'Validation must be independent', 'The repo must prove every claim'],
    },
    {
        'title': 'The BAND',
        'subtitle': 'Foreman / Smith / Inspector / Stresser',
        'bullets': ['Foreman runs dispatch and reporting', 'Smith implements and verifies', 'Inspector reviews and accepts deltas', 'Stresser probes defects and pressure tests'],
        'warning': '[HUMAN: RECORD BAND DESKTOP ROOM]',
    },
    {
        'title': 'Generic mandates',
        'subtitle': 'Mechanically linted and track-agnostic',
        'bullets': ['4 mandates, 0 violations', 'No track vocabulary leaks in the prompts', 'The factory can be repurposed across tasks'],
    },
    {
        'title': 'Stage 1 result',
        'subtitle': 'SHIPPED and locally verified',
        'bullets': ['Official harness: 147/147 PASS', 'Private smoke: 145/145 PASS', 'Isolated Docker constraints: network none, 2 CPUs, 2 GB RAM'],
    },
    {
        'title': 'How it catches bad work',
        'subtitle': 'C1 / C2 are real defects, not fictional drama',
        'bullets': ['Stresser raised C1: empty-body 422 vs 400', 'Smith fixed it and found C2: cold-start index issue', 'Inspector accepted the deltaed fix'],
    },
    {
        'title': 'Autonomy ledger',
        'subtitle': 'Honesty beats polish',
        'bullets': ['4 human messages total', '3 OpenCode timeouts', '~1h55m stall', 'FATAL at 2026-10-05T12:39:09Z'],
    },
    {
        'title': 'Timeline and cost',
        'subtitle': 'Stage 1 took ~44 minutes',
        'bullets': ['Dispatch: 2026-10-05T09:15:48Z', 'Final report: 2026-10-05T10:00:00Z', 'Spend figure: not captured in archive', 'Human fill-in still required'],
    },
    {
        'title': 'What did not ship',
        'subtitle': 'The honest submission boundary',
        'bullets': ['Stage 2: draft only, not committed', 'Stages 3 and 4: not reached', 'Real Band room recording still required', 'Repo publish and form submission remain pending'],
    },
]

font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
font_med = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

for idx, slide in enumerate(slides, start=1):
    image = Image.new('RGB', (1920, 1080), (9, 16, 32))
    draw = ImageDraw.Draw(image)

    # gradient-like overlays
    for y in range(0, 1080, 8):
        color = tuple(min(255, 9 + y // 6) for _ in range(3))
        draw.line([(0, y), (1920, y)], fill=color)

    draw.rounded_rectangle((80, 80, 1840, 1000), radius=30, fill=(17, 25, 40), outline=(80, 113, 210), width=4)
    draw.rounded_rectangle((120, 140, 1800, 180), radius=20, fill=(31, 41, 55), outline=(107, 160, 255), width=2)

    title_font = ImageFont.truetype(font_path, 64)
    subtitle_font = ImageFont.truetype(font_med, 28)
    body_font = ImageFont.truetype(font_med, 32)
    warning_font = ImageFont.truetype(font_path, 28)

    draw.text((150, 170), slide['title'], fill=(230, 240, 255), font=title_font)
    draw.text((150, 245), slide['subtitle'], fill=(155, 176, 212), font=subtitle_font)

    y = 360
    for bullet in slide['bullets']:
        draw.text((150, y), '• ' + bullet, fill=(240, 245, 255), font=body_font)
        y += 70

    if 'warning' in slide:
        box = (130, 830, 1790, 920)
        draw.rounded_rectangle(box, radius=25, fill=(72, 27, 8), outline=(255, 170, 0), width=4)
        draw.text((170, 855), slide['warning'], fill=(255, 245, 200), font=warning_font)

    draw.text((150, 980), 'Pocketful Factory submission package • evidence-backed and honest about limits', fill=(170, 190, 215), font=ImageFont.truetype(font_med, 20))
    image.save(OUT_DIR / f'slide-{idx:02d}.png')

# Create the MP4 via ffmpeg.
frames_pattern = str(OUT_DIR / 'slide-%02d.png')
cmd = [
    'ffmpeg', '-y',
    '-framerate', '1/5',
    '-i', frames_pattern,
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart',
    str(MP4_OUT),
]
subprocess.run(cmd, check=True)
print(f'Created {MP4_OUT}')
