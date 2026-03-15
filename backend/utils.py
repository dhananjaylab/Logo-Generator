import os
from pathlib import Path


def ensure_output_directory(directory: str = "generated_logos") -> str:
    """
    Ensure output directory exists and return its path.
    
    Args:
        directory: Directory name or path
        
    Returns:
        Full path to the directory
    """
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)


def get_output_path(filename: str, directory: str = "generated_logos") -> str:
    """
    Get full path for an output file.
    
    Args:
        filename: Name of the file
        directory: Output directory
        
    Returns:
        Full path to the file
    """
    output_dir = ensure_output_directory(directory)
    return os.path.join(output_dir, filename)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename
