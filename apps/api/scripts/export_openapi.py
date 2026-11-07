"""Write FastAPI's OpenAPI schema to a file (input of `make types`).

Usage: python -m scripts.export_openapi OUTPUT.json
"""

import json
import sys
from pathlib import Path

from holdsup.main import app


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m scripts.export_openapi OUTPUT.json")
    Path(sys.argv[1]).write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
