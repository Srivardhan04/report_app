"""Utility helpers."""

import re
from typing import Optional


def sanitize_filename(name: str) -> str:
    """Remove unsafe characters from a filename."""
    return re.sub(r'[^\w\-.]', '_', name)


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
