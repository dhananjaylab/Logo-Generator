import hashlib
import os
from pathlib import Path
from typing import Optional


def ensure_output_directory(directory: str = "generated_logos") -> str:
    """
    Ensure output directory (and any parents) exist. Returns the path string.
    Supports nested paths like 'generated_logos/openai'.
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


def anonymise_ip(ip: Optional[str]) -> Optional[str]:
    """
    Return a short, one-way hash of an IP address for pseudonymous storage.

    Requirements:
    - IP_HASH_SALT must be set in the environment; if absent, returns None so
      no IP-derived data is stored at all (fail-safe for GDPR compliance).
    - The salt must be kept secret and stable — rotating it orphans all existing
      hashes, making them unrelatable to future requests.
    - Returns the first 16 hex characters of SHA-256(salt:ip), which is enough
      to correlate requests from the same IP without storing the address itself.

    Usage:
        anonymise_ip("203.0.113.42")  →  "a3f8c1d290e45b67"  (example)
        anonymise_ip(None)            →  None
    """
    if not ip:
        return None
    salt = os.getenv("IP_HASH_SALT", "")
    if not salt:
        # Refuse to store anything rather than store an unsalted hash.
        return None
    digest = hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()
    return digest[:16]
