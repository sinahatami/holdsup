"""Strip secrets from text before it reaches logs, attempt records, or terminal output."""

import os
import re
from collections.abc import Iterable, Mapping

# Common API-key shapes (Groq gsk_, OpenAI/OpenRouter sk-/sk-or-, Google AIza, bearer tokens).
_KEY_PATTERNS = re.compile(
    r"(gsk_[A-Za-z0-9]{8,}|sk-or-v1-[A-Za-z0-9]{8,}|sk-[A-Za-z0-9_\-]{8,}|AIza[0-9A-Za-z_\-]{20,}"
    r"|(?i:bearer)\s+[A-Za-z0-9._\-]{8,})"
)
REDACTED = "[REDACTED]"


def secret_values(env: Mapping[str, str] | None = None, names: Iterable[str] = ()) -> list[str]:
    """Values of *_API_KEY variables (and any extra names) that are long enough to be secrets."""
    env = os.environ if env is None else env
    wanted = {n for n in env if n.endswith(("_API_KEY", "_TOKEN"))} | set(names)
    return [env[n] for n in wanted if n in env and len(env[n]) >= 8]


def redact(text: str, secrets: Iterable[str] = ()) -> str:
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, REDACTED)
    return _KEY_PATTERNS.sub(REDACTED, text)
