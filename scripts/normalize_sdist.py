from __future__ import annotations

import argparse
import copy
import gzip
import io
import os
from pathlib import Path
import tarfile
import tempfile
from typing import BinaryIO


def normalize_sdist(path: Path, *, epoch: int) -> None:
    if epoch < 0:
        raise ValueError("epoch must be non-negative")

    entries: list[tuple[tarfile.TarInfo, bytes | None]] = []
    with tarfile.open(path, "r:gz") as source:
        for member in source.getmembers():
            extracted = source.extractfile(member) if member.isfile() else None
            entries.append((member, extracted.read() if extracted is not None else None))

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as raw:
            _write_normalized_archive(raw, entries=entries, epoch=epoch)
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _write_normalized_archive(
    raw: BinaryIO,
    *,
    entries: list[tuple[tarfile.TarInfo, bytes | None]],
    epoch: int,
) -> None:
    with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=epoch) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as target:
            for original, payload in entries:
                member = copy.copy(original)
                member.mtime = epoch
                member.uid = 0
                member.gid = 0
                member.uname = ""
                member.gname = ""
                member.pax_headers = {
                    key: value
                    for key, value in member.pax_headers.items()
                    if key not in {"atime", "ctime", "mtime"}
                }
                target.addfile(
                    member,
                    io.BytesIO(payload) if payload is not None else None,
                )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize Python sdist metadata for reproducible archives.",
    )
    parser.add_argument("sdists", nargs="+", type=Path)
    parser.add_argument(
        "--epoch",
        type=int,
        default=_source_date_epoch(),
        help="archive timestamp; defaults to SOURCE_DATE_EPOCH",
    )
    args = parser.parse_args()
    if args.epoch is None:
        parser.error("--epoch or SOURCE_DATE_EPOCH is required")

    for sdist in args.sdists:
        normalize_sdist(sdist, epoch=args.epoch)
    return 0


def _source_date_epoch() -> int | None:
    value = os.environ.get("SOURCE_DATE_EPOCH")
    return int(value) if value is not None else None


if __name__ == "__main__":
    raise SystemExit(main())
