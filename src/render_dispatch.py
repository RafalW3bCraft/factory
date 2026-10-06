#!/usr/bin/env python3
"""render_dispatch.py — CLI shim delegating to factory.render_dispatch."""

from __future__ import annotations

from factory.render_dispatch import TEMPLATE_ALIASES, main, render, resolve_template_path

__all__ = ["TEMPLATE_ALIASES", "main", "render", "resolve_template_path"]

if __name__ == "__main__":
    main()
