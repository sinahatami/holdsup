"""Saved model replies, so a run spends no quota on a request it has already made.

The smoke gate runs on every pull request that could change a verdict, against the same
free-tier keys as the nightly run, and most of those pull requests change no prompt at all. A
`ReplayClient` answers a request it has a saved reply for from the store, and sends anything
else (a changed prompt, another model, new series data in a plan prompt) to the provider,
saving what comes back. Only replies are saved, never failures, so a request a rate limit
turned away is asked again next time.

The key is the provider, its model and the whole request, so a reply is only ever replayed
for exactly the request that produced it. A replayed run measures the code, not the models'
day-to-day variation; the nightly run records (`replay=False`): it asks every request afresh,
so a provider that changes its model is still noticed, and it leaves the store the PR runs
start from.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from holdsup.router.client import ChatRequest, ChatResponse, SupportsChat, ToolCall
from holdsup.router.config import ProviderConfig

FORMAT = 1  # bump when the key or the file layout changes: old replies are then never matched


def request_key(provider: ProviderConfig, request: ChatRequest) -> str:
    """The same provider, model and request give the same key; anything else another one."""
    body = {
        "format": FORMAT,
        "provider": provider.name,
        "model": provider.model,
        "messages": list(request.messages),
        "response_format": request.response_format,
        "tools": list(request.tools) if request.tools is not None else None,
        "tool_choice": request.tool_choice,
        "temperature": request.temperature,
    }
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class ReplayStore:
    """One JSON file per reply in `directory`."""

    directory: Path
    hits: int = 0
    saved: int = 0
    _used: set[str] = field(default_factory=set)

    def get(self, key: str) -> ChatResponse | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            response = ChatResponse(
                content=data["content"],
                tool_calls=tuple(ToolCall(**t) for t in data["tool_calls"]),
                prompt_tokens=data["prompt_tokens"],
                completion_tokens=data["completion_tokens"],
            )
        except (ValueError, KeyError, TypeError):  # a damaged file: ask the provider again
            return None
        self.hits += 1
        self._used.add(key)
        return response

    def put(self, key: str, response: ChatResponse) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        data = asdict(response) | {"tool_calls": [asdict(t) for t in response.tool_calls]}
        tmp = self._path(key).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        tmp.replace(self._path(key))
        self.saved += 1
        self._used.add(key)

    def prune(self) -> int:
        """Remove the replies this run did not use (old prompts, old models); returns how many.
        Call it only after a whole run, or the replies for the texts not yet run go too."""
        removed = 0
        for path in self.directory.glob("*.json") if self.directory.exists() else ():
            if path.stem not in self._used:
                path.unlink()
                removed += 1
        return removed

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"


class ReplayClient:
    """A `SupportsChat` that answers from `store` when it can (`replay=True`) and saves every
    reply it gets from `inner`. With `replay=False` it only records."""

    def __init__(self, inner: SupportsChat, store: ReplayStore, *, replay: bool = True) -> None:
        self._inner = inner
        self._store = store
        self._replay = replay

    def has_key(self, provider: ProviderConfig) -> bool:
        return self._inner.has_key(provider)

    async def complete(self, provider: ProviderConfig, request: ChatRequest) -> ChatResponse:
        key = request_key(provider, request)
        if self._replay and (saved := self._store.get(key)) is not None:
            return saved
        response = await self._inner.complete(provider, request)
        self._store.put(key, response)
        return response
