from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, engine  # noqa: E402
from app.geo_ids import file_sha256  # noqa: E402
from app.geo_ingest_service import ingest_geo_document  # noqa: E402
from app.models import Base  # noqa: E402
from app.settings import settings  # noqa: E402


@dataclass(frozen=True)
class Candidate:
    path: Path
    digest: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync local Geo RAG documents into the configured cloud stores.")
    parser.add_argument(
        "--directory",
        default=str(ROOT / ".data" / "geo_rag_documents"),
        help="Directory containing PDF/TXT/MD documents.",
    )
    parser.add_argument("--limit", type=int, default=1000, help="Maximum unique documents to ingest.")
    parser.add_argument("--dry-run", action="store_true", help="Print the selected files without ingesting.")
    parser.add_argument("--force", action="store_true", help="Rebuild documents that already exist.")
    args = parser.parse_args()

    directory = _resolve_directory(args.directory)
    candidates = _unique_candidates(directory)
    if args.limit > 0:
        candidates = candidates[: args.limit]

    print(f"[sync] database={_redact_url(settings.database_url)}")
    print(f"[sync] qdrant={settings.qdrant_url} collection={settings.qdrant_collection}")
    print(f"[sync] storageBackend={settings.geo_rag_storage_backend}")
    print(f"[sync] embedding={settings.geo_rag_embedding_provider} {settings.geo_rag_embedding_model}")
    print(f"[sync] directory={directory}")
    print(f"[sync] uniqueDocuments={len(candidates)}")
    for index, candidate in enumerate(candidates, start=1):
        print(f"[sync] {index:03d} {candidate.path.name} sha256={candidate.digest[:12]}")

    if args.dry_run:
        return 0

    Base.metadata.create_all(bind=engine)
    succeeded = 0
    failed = 0
    with SessionLocal() as db:
        for index, candidate in enumerate(candidates, start=1):
            print(f"[sync] ingesting {index}/{len(candidates)} {candidate.path.name}")
            try:
                result = ingest_geo_document(
                    db,
                    {
                        "filePath": str(candidate.path),
                        "title": _title_from_path(candidate.path),
                        "force": bool(args.force),
                    },
                )
                succeeded += 1
                print(
                    "[sync] indexed "
                    f"documentId={result.get('documentId')} "
                    f"units={result.get('units')} "
                    f"storage={result.get('storageUri')}"
                )
            except Exception as exc:
                db.rollback()
                failed += 1
                print(f"[sync] failed {candidate.path.name}: {exc}")

    print(f"[sync] done succeeded={succeeded} failed={failed}")
    return 1 if failed else 0


def _resolve_directory(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    resolved = path.resolve()
    if not resolved.is_dir():
        raise SystemExit(f"Document directory does not exist: {resolved}")
    return resolved


def _unique_candidates(directory: Path) -> list[Candidate]:
    by_digest: dict[str, Path] = {}
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".txt", ".md"}:
            continue
        digest = file_sha256(path)
        current = by_digest.get(digest)
        if current is None or _prefer_path(path, current):
            by_digest[digest] = path
    return [Candidate(path=path, digest=digest) for digest, path in sorted(by_digest.items(), key=lambda item: item[1].name)]


def _prefer_path(candidate: Path, current: Path) -> bool:
    return _path_rank(candidate) < _path_rank(current)


def _path_rank(path: Path) -> tuple[int, int, str]:
    name = path.name
    generated_penalty = 0
    if name.startswith("paper-paper-"):
        generated_penalty = 3
    elif name.startswith("paper-"):
        generated_penalty = 1
    return (generated_penalty, len(name), name)


def _title_from_path(path: Path) -> str:
    title = path.stem
    if title.startswith("paper-"):
        title = title.removeprefix("paper-")
    return title[:200] or path.stem


def _redact_url(url: str) -> str:
    if "@" not in url:
        return url
    prefix, suffix = url.rsplit("@", 1)
    scheme = prefix.split("://", 1)[0] if "://" in prefix else "postgresql"
    return f"{scheme}://***@{suffix}"


if __name__ == "__main__":
    raise SystemExit(main())
