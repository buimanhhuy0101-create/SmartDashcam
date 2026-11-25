import hashlib
from pathlib import Path


def compute_sha256(file_path: Path) -> str:
    """Tính mã băm SHA-256 của tệp theo từng khối 64KB."""
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_sha256(file_path: Path, expected_checksum: str | None) -> bool:
    """Kiểm tra tính toàn vẹn của tệp dựa trên checksum_sha256."""
    if not expected_checksum:
        return True
    actual = compute_sha256(file_path)
    return actual.lower() == expected_checksum.strip().lower()