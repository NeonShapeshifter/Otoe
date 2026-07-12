from __future__ import annotations

import gzip
import hashlib
from io import BytesIO
from pathlib import Path
import tarfile

from scripts.normalize_sdist import normalize_sdist


def test_normalize_sdist_produces_identical_archives(tmp_path: Path):
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    _write_sdist(first, timestamp=100)
    _write_sdist(second, timestamp=200)

    normalize_sdist(first, epoch=42)
    normalize_sdist(second, epoch=42)

    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(
        second.read_bytes()
    ).digest()
    with tarfile.open(first, "r:gz") as archive:
        member = archive.getmember("otoe-1.0/README.md")
        assert member.mtime == 42
        assert member.uid == 0
        assert member.gid == 0
        extracted = archive.extractfile(member)
        assert extracted is not None
        assert extracted.read() == b"Otoe\n"


def _write_sdist(path: Path, *, timestamp: int) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=timestamp) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                payload = b"Otoe\n"
                member = tarfile.TarInfo("otoe-1.0/README.md")
                member.size = len(payload)
                member.mtime = timestamp
                member.uid = timestamp
                member.gid = timestamp
                archive.addfile(member, BytesIO(payload))
