"""
Small helper for writing gbrain-compatible frontmatter markdown files.
"""

import re
import yaml
from pathlib import Path


def slugify(value: str) -> str:
    """Make a filesystem-safe filename out of an arbitrary API-provided ID."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", value)


def write_frontmatter_file(directory: Path, filename_stem: str, frontmatter: dict, body: str) -> Path:
    """
    Writes a single .md file with YAML frontmatter + body text, in the shape
    gbrain expects for `gbrain sync` / `gbrain import`.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{slugify(filename_stem)}.md"

    fm_block = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    content = f"---\n{fm_block}\n---\n\n{body.strip()}\n"

    path.write_text(content, encoding="utf-8")
    return path