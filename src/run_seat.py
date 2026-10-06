#!/usr/bin/env python3
"""run_seat.py — CLI shim delegating to factory.run_seat."""

from __future__ import annotations

from factory.run_seat import extract_mandate_model, main, read_mandate

__all__ = ["extract_mandate_model", "main", "read_mandate"]

if __name__ == "__main__":
    main()
