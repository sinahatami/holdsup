"""List the model ids each configured provider actually serves to this key. Not part of CI.

Usage (from the repo root, with keys in .env):  make list-models [ARGS="--all"]
Calls GET {base_url}/models once per distinct base URL + key. Keys are never printed.
OpenRouter's list is long: by default only `:free` models are shown, with whether they support
`tools` and `response_format` / `structured_outputs`.
"""

import argparse
import asyncio
import sys
from urllib.parse import urlparse

from holdsup.router.client import ModelInfo, OpenAICompatibleClient
from holdsup.router.config import ProviderConfig, load_router_config
from holdsup.router.errors import ProviderError


def _on_domain(url: str, domain: str) -> bool:
    """True if the URL's host is `domain` or a subdomain of it (not just a substring)."""
    host = (urlparse(url).hostname or "").lower()
    return host == domain or host.endswith(f".{domain}")


def _visible(provider: ProviderConfig, model: ModelInfo, show_all: bool) -> bool:
    if show_all:
        return True
    if _on_domain(provider.base_url, "openrouter.ai"):
        return model.id.endswith(":free")
    if _on_domain(provider.base_url, "googleapis.com"):
        return "gemini" in model.id and "embedding" not in model.id
    return True


def _flags(model: ModelInfo) -> str:
    parts = []
    if model.context:
        parts.append(f"ctx {model.context}")
    if model.active is False:
        parts.append("INACTIVE")
    if model.supported_parameters is not None:
        params = set(model.supported_parameters)
        parts.append("tools" if "tools" in params else "no-tools")
        has_schema = {"structured_outputs", "response_format"} & params
        parts.append("json" if has_schema else "no-json")
    return ", ".join(parts)


async def run(show_all: bool) -> int:
    config = load_router_config()
    client = OpenAICompatibleClient()
    seen: set[tuple[str, str]] = set()
    status = 0
    for provider in config.providers:
        key = (provider.base_url, provider.api_key_env)
        if key in seen:
            continue
        seen.add(key)
        configured = sorted(p.model for p in config.providers if (p.base_url, p.api_key_env) == key)
        print(f"\n## {provider.base_url}")
        if not client.has_key(provider):
            print("   key not set")
            continue
        try:
            models = await client.list_models(provider)
        except ProviderError as exc:
            print(f"   FAILED: {exc}")
            status = 1
            continue
        ids = {m.id for m in models}
        for model_id in configured:
            mark = "ok" if model_id in ids else "MISSING"
            print(f"   configured {model_id}: {mark}")
        shown = [m for m in models if _visible(provider, m, show_all)]
        print(f"   {len(models)} models available, showing {len(shown)}:")
        for m in shown:
            flags = _flags(m)
            print(f"   - {m.id}" + (f"  [{flags}]" if flags else ""))
    return status


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="make list-models")
    parser.add_argument("--all", action="store_true", help="show every model, no filtering")
    return asyncio.run(run(parser.parse_args(argv).all))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
