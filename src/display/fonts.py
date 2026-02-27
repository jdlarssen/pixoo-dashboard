"""BDF-to-PIL font conversion and font registry."""

import logging
import os
from pathlib import Path

from PIL import BdfFontFile, ImageFont

logger = logging.getLogger(__name__)


def convert_bdf_to_pil(bdf_path: str, output_dir: str | None = None) -> str:
    """Convert a BDF font file to PIL format (.pil + .pbm files).

    Args:
        bdf_path: Path to the BDF font file.
        output_dir: Directory to write converted files. Defaults to same directory as bdf_path.

    Returns:
        Path to the generated .pil file.
    """
    bdf_path = str(bdf_path)
    if output_dir is None:
        output_dir = os.path.dirname(bdf_path)

    # Derive output path without extension (BdfFontFile.save adds .pil and .pbm)
    base_name = os.path.splitext(os.path.basename(bdf_path))[0]
    pil_base = os.path.join(output_dir, base_name)

    with open(bdf_path, "rb") as fp:
        font = BdfFontFile.BdfFontFile(fp)
        font.save(pil_base)

    return pil_base + ".pil"


def load_fonts(font_dir: str | Path) -> dict[str, ImageFont.ImageFont]:
    """Load all BDF fonts from a directory, converting to PIL format if needed.

    Scans for .bdf files, converts any that don't have a corresponding .pil file,
    then loads and returns all PIL fonts keyed by font name (e.g., "7x13", "5x8").

    Args:
        font_dir: Directory containing BDF font files.

    Returns:
        Dictionary mapping font names to loaded PIL ImageFont objects.
    """
    font_dir = str(font_dir)
    if not os.path.isdir(font_dir):
        raise FileNotFoundError(f"Font directory not found: {font_dir}")

    fonts: dict[str, ImageFont.ImageFont] = {}

    for filename in sorted(os.listdir(font_dir)):
        if not filename.endswith(".bdf"):
            continue

        font_name = os.path.splitext(filename)[0]
        bdf_path = os.path.join(font_dir, filename)
        pil_path = os.path.join(font_dir, font_name + ".pil")

        try:
            if not os.path.exists(pil_path):
                convert_bdf_to_pil(bdf_path, font_dir)
            fonts[font_name] = ImageFont.load(pil_path)
        except (OSError, SyntaxError) as exc:
            logger.error("Failed to load font %s: %s", font_name, exc)

    return fonts
