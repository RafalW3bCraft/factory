#!/usr/bin/env python3
"""analyze_room.py — CLI shim delegating to factory.analyze_room."""

from __future__ import annotations

from factory.analyze_room import fmt, main, messages, parse_time, walk

__all__ = ["fmt", "main", "messages", "parse_time", "walk"]

if __name__ == "__main__":
    main()
