#!/usr/bin/env python3
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape
from reportlab.lib import colors
from reportlab.lib.units import inch

WIDTH, HEIGHT = 1920, 1080
PAGE = (WIDTH, HEIGHT)


def add_bg(c, title_color):
    c.setFillColor(colors.HexColor('#0B1020'))
    c.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#111827'))
    c.rect(80, 80, WIDTH - 160, HEIGHT - 160, fill=1, stroke=0)
    c.setFillColor(title_color)
    c.rect(80, 80, WIDTH - 160, 8, fill=1, stroke=0)


def title_block(c, title, subtitle=None):
    c.setFont('Helvetica-Bold', 48)
    c.setFillColor(colors.HexColor('#E5F0FF'))
    c.drawString(120, 920, title)
    if subtitle:
        c.setFont('Helvetica', 22)
        c.setFillColor(colors.HexColor('#9FB3D1'))
        c.drawString(120, 870, subtitle)


def footnote(c, text):
    c.setFont('Helvetica', 12)
    c.setFillColor(colors.HexColor('#B7C7DF'))
    c.drawString(120, 110, text)


def draw_slide(c, slide_num, title, body_lines, bg_color, foot_text):
    add_bg(c, bg_color)
    c.setFont('Helvetica-Bold', 30)
    c.setFillColor(colors.HexColor('#B5C9E8'))
    c.drawString(120, 980, f"Pocketful Factory — slide {slide_num}")
    title_block(c, title)
    c.setFont('Helvetica', 26)
    c.setFillColor(colors.HexColor('#E4ECF9'))
    y = 760
    for line in body_lines:
        c.drawString(120, y, line)
        y -= 52
    footnote(c, foot_text)
    c.showPage()


def main():
    pdf = canvas.Canvas('submission-assets/slides/pocketful-factory.pdf', pagesize=PAGE)
    slides = [
        (
            'Pocketful Factory: a four-seat dark factory that proves its own work',
            [
                'Track: pocketful',
                'Hackathon: WeAreDevelopers x BAND “Dark Factory”',
                'Goal: autonomous review, validation, and staged submission proof',
            ],
            '#5B8DEF',
            'Evidence: room.json; room id 48bd09b2-3c1e-426c-9beb-29d79b6f8d91; 683 total messages.',
        ),
        (
            'The problem and the track',
            [
                'The system is a wallet and peer-to-peer payments service.',
                'The core constraint is conservation of funds and validated ledger behavior.',
                'Every human message is disclosed; this run was not a single dispatch.',
            ],
            '#2E7D6B',
            'Evidence: docs/FACT_SHEET.md §10; room.json; Stage 1 minimum eligibility.',
        ),
        (
            'The BAND: Foreman / Smith / Inspector / Stresser',
            [
                'Foreman: orchestrates dispatch and final reporting.',
                'Smith: implements and self-verifies the service fix path.',
                'Inspector: independent validation and delta-acceptance.',
                'Stresser: adversarial testing and defect probing.',
            ],
            '#7F5AF0',
            'Evidence: mandates/foreman.md, smith.md, inspector.md, stresser.md; Inspector model = MiniMaxAI/MiniMax-M2.5.',
        ),
        (
            'Generic mandates, mechanically linted',
            [
                'Four mandates; lint_gate reported 4 mandates, 0 violations.',
                'The mandate check rejects track-specific vocabulary and endpoint details.',
                'This keeps the work reusable beyond the pocketful track.',
            ],
            '#3B82F6',
            'Evidence: python3 factory/src/lint_mandates.py -> 4 mandates, 0 violations.',
        ),
        (
            'Stage 1 result: SHIPPED',
            [
                'Verified result: 147/147 official harness pass on the shipped revision.',
                'Private smoke suite: 145/145 pass.',
                'The service was validated in an isolated Docker network with CPU and memory caps.',
            ],
            '#E46A43',
            'Evidence: docs/FACT_SHEET.md §7; room messages f52c30d5, e5630170, b054d56f.',
        ),
        (
            'How it catches bad work',
            [
                'C1: empty-body request returned 422 instead of 400; Stresser raised the concern.',
                'Smith fixed the issue and found C2: cold-start index failure before first reset.',
                'Inspector accepted the first revision and then the deltaed fix.',
            ],
            '#C56F26',
            'Evidence: room.json, 09:51:47Z C1 concern, 09:57:03Z fix commit 5620886, 09:59:41Z delta accepted.',
        ),
        (
            'Honest autonomy ledger',
            [
                '4 human messages total: initial dispatch, one timeout re-dispatch, one continue nudge, one steering note.',
                '3 OpenCode timeouts were recorded in the room.',
                '~1h55m stall occurred between timeout #2 and the human continue note.',
                'FATAL opencode server died at 2026-10-05T12:39:09Z.',
            ],
            '#6B7280',
            'Evidence: docs/FACT_SHEET.md §§3-4; room.json. Human work is disclosed, not hidden.',
        ),
        (
            'Timeline and cost',
            [
                'Stage 1 dispatch: 2026-10-05T09:15:48Z.',
                'Final Stage 1 report: 2026-10-05T10:00:00Z.',
                'Approximate duration: ~44 minutes.',
                'Spend figure: not captured in the repo archive; needs human fill-in.',
            ],
            '#2C7A7A',
            'Evidence: docs/FACT_SHEET.md §5; room.json run window; spend figure remains unfilled by human input.',
        ),
        (
            'What did not ship',
            [
                'Stage 2 was draft-only and not committed to the result repo.',
                'Stages 3 and 4 were not reached.',
                'The presentation video includes cropped Band Desktop room excerpts.',
                'A public GitHub push remains an operator action (local commits only).',
            ],
            '#475569',
            'Evidence: docs/FACT_SHEET.md §9 and §11; room.json not enough to fake a room recording.',
        ),
        (
            'Reproduce it',
            [
                'Build: docker build -t pocketful-s1 ./stage-1',
                'Run: docker run -d --rm --network none --cpus=2 --memory=2048m -p 8080:8080 --name pocketful-s1 pocketful-s1',
                'Verify: curl -s localhost:8080/health and POST /_test/reset',
                'Repo: https://github.com/<user>/<repo>  (publish required by human operator)',
            ],
            '#8A5A44',
            'Evidence: README.md run instructions; Stage 1 verification check list in the repo and the room evidence.',
        ),
    ]

    for idx, s in enumerate(slides, start=1):
        draw_slide(pdf, idx, s[0], s[1], s[2], s[3])

    pdf.save()
    print('Created submission-assets/slides/pocketful-factory.pdf')


if __name__ == '__main__':
    main()
