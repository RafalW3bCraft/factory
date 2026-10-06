#!/usr/bin/env python3
"""lint_mandates.py — CLI shim delegating to factory.lint_mandates."""

from __future__ import annotations

from factory.lint_mandates import SECRET_PATTERNS, lint, main

__all__ = ["SECRET_PATTERNS", "lint", "main"]

if __name__ == "__main__":
    main()
