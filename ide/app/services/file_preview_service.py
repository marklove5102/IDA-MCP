"""File preview service: determines how to display a file."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class PreviewKind(str, Enum):
    TEXT = "text"
    HEX = "hex"
    IMAGE = "image"


@dataclass(slots=True)
class PreviewResult:
    """Result of file preview routing."""

    kind: PreviewKind
    path: str
    text: str | None = None


_IMAGE_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".svg",
        ".ico",
        ".webp",
        ".tif",
        ".tiff",
    }
)


def is_image_file(path: str) -> bool:
    return Path(path).suffix.lower() in _IMAGE_EXTENSIONS


def classify_file(path: str) -> PreviewResult:
    """Classify a file for preview display.

    Routing: image → text → hex (fallback for binary).
    """
    if is_image_file(path):
        return PreviewResult(kind=PreviewKind.IMAGE, path=path)

    try:
        data = Path(path).read_bytes()
        sample = data[:8192]
        if b"\x00" in sample:
            raise ValueError("binary file")
        text = data.decode("utf-8")
        return PreviewResult(kind=PreviewKind.TEXT, path=path, text=text)
    except (UnicodeDecodeError, ValueError):
        return PreviewResult(kind=PreviewKind.HEX, path=path)
