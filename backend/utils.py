import os
from pathlib import Path


def ensure_output_directory(directory: str = "generated_logos") -> str:
    """
    Ensure output directory (and any parents) exist. Returns the path string.
    Supports nested paths like 'generated_logos/dalle'.
    """
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)


def get_output_path(filename: str, directory: str = "generated_logos") -> str:
    """
    Get full path for an output file, creating the directory if needed.
    """
    output_dir = ensure_output_directory(directory)
    return os.path.join(output_dir, filename)


def sanitize_filename(filename: str) -> str:
    """
    Remove characters that are illegal in filenames on Windows/Linux/macOS.
    """
    invalid = '<>:"/\\|?* '
    for ch in invalid:
        filename = filename.replace(ch, "_")
    return filename