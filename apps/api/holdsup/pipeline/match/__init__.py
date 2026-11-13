"""Step 3, find the indicator: vector top 8 (coverage-filtered), the reranker orders them,
and the model picks unless the reranker's margin is wide enough to take its first.

The model may call `search_catalog`, `get_indicator_meta` and `list_geos` (at most 4 tool
calls in all). Code checks its pick: it must be an id the model was shown and must cover the
claim's place. No pick or low confidence means "can't check".

Modules: `candidates` (search kept to the claim's place), `prompt` (what the model reads),
`tools` (the tool registry), `second_look` (when to ask again), `rerank` (the reranker's
order and margin), `matcher` (the conversation).
"""

from holdsup.pipeline.match.candidates import SEARCH_POOL, TOP_K, CandidatePool
from holdsup.pipeline.match.matcher import MAX_ALTERNATIVES, Matcher
from holdsup.pipeline.match.model import (
    Candidate,
    Confidence,
    MatchAnswer,
    MatchResult,
    MatchRun,
    ToolUse,
)
from holdsup.pipeline.match.prompt import (
    FINAL_PROMPT,
    MATCH_SYSTEM,
    claim_message,
    needs_level_series,
    yearly_note,
)
from holdsup.pipeline.match.rerank import SKIP_MARGIN, Ranked, Reranker, rerank
from holdsup.pipeline.match.tools import MAX_TOOL_CALLS, TOOL_REGISTRY, TOOLS

__all__ = [
    "FINAL_PROMPT",
    "MATCH_SYSTEM",
    "MAX_ALTERNATIVES",
    "MAX_TOOL_CALLS",
    "SEARCH_POOL",
    "SKIP_MARGIN",
    "TOOLS",
    "TOOL_REGISTRY",
    "TOP_K",
    "Candidate",
    "CandidatePool",
    "Confidence",
    "MatchAnswer",
    "MatchResult",
    "MatchRun",
    "Matcher",
    "Ranked",
    "Reranker",
    "ToolUse",
    "claim_message",
    "needs_level_series",
    "rerank",
    "yearly_note",
]
