"""`make catalog`: validate packages/catalog, embed every entry, and sync the indicators table.

Entries missing from the YAML are deleted, so the table always mirrors the catalog version.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from holdsup.catalog.embed import Embedder, default_embedder
from holdsup.catalog.schema import Catalog, CatalogError, load_catalog
from holdsup.config import get_settings
from holdsup.db.models import Indicator
from holdsup.db.session import get_sessionmaker


def rows(catalog: Catalog, embedder: Embedder) -> list[dict[str, object]]:
    vectors = embedder.embed([s.embedding_text() for s in catalog.indicators])
    return [
        {
            "id": s.id,
            "source": s.source.value,
            "source_code": s.source_code,
            "name": s.name,
            "aliases": list(s.aliases),
            "definition": s.definition,
            "unit": s.unit,
            "frequency": s.frequency.value,
            "geo_coverage": list(s.geo_coverage),
            "first_year": s.first_year,
            "last_year": s.last_year,
            "related": list(s.related),
            "filters": dict(s.filters),
            "catalog_version": catalog.version,
            "embedding": vector,
        }
        for s, vector in zip(catalog.indicators, vectors, strict=True)
    ]


async def sync(
    catalog: Catalog, embedder: Embedder, sessionmaker: async_sessionmaker[AsyncSession]
) -> int:
    values = rows(catalog, embedder)
    ids = [str(v["id"]) for v in values]
    async with sessionmaker() as session, session.begin():
        await session.execute(delete(Indicator).where(Indicator.id.not_in(ids)))
        if values:
            stmt = insert(Indicator).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Indicator.id],
                set_={k: stmt.excluded[k] for k in values[0] if k != "id"},
            )
            await session.execute(stmt)
    return len(values)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m holdsup.catalog.load")
    parser.add_argument(
        "root", nargs="?", type=Path, help="catalog dir (default: packages/catalog)"
    )
    parser.add_argument("--check", action="store_true", help="validate only; no embeddings or DB")
    args = parser.parse_args(argv)
    settings = get_settings()
    root: Path = args.root or settings.catalog_dir
    try:
        catalog = load_catalog(root)
    except CatalogError as exc:
        print(exc, file=sys.stderr)
        return 1
    if args.check:
        print(f"catalog {catalog.version}: {len(catalog.indicators)} valid entries")
        return 0
    embedder = default_embedder(settings.fastembed_cache_path)
    count = asyncio.run(sync(catalog, embedder, get_sessionmaker()))
    print(f"catalog {catalog.version}: loaded {count} indicators")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
