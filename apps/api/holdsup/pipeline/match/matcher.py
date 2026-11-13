"""The match: rerank the candidates, and when the reranker is not clear enough, the
conversation: show the candidates, answer tool calls, take a second look, and check the
model's pick."""

from dataclasses import dataclass, field

from openai.types.chat import ChatCompletionMessageParam

from holdsup.catalog.schema import Catalog
from holdsup.catalog.search import CatalogSearch
from holdsup.pipeline.claim import ClaimSpec
from holdsup.pipeline.match.candidates import CandidatePool
from holdsup.pipeline.match.model import Candidate, MatchAnswer, MatchResult, MatchRun
from holdsup.pipeline.match.prompt import (
    FINAL_PROMPT,
    MATCH_SYSTEM,
    claim_message,
    parse_answer,
    tool_calls_message,
)
from holdsup.pipeline.match.rerank import SKIP_MARGIN, Ranked, Reranker, rerank
from holdsup.pipeline.match.second_look import second_look
from holdsup.pipeline.match.tools import MAX_TOOL_CALLS, TOOLS, answer_tool_call
from holdsup.places import place_name
from holdsup.router import Router, Use

MAX_ALTERNATIVES = 3


@dataclass
class Matcher:
    router: Router
    catalog: Catalog
    search: CatalogSearch
    use: Use = Use.LIVE
    reranker: Reranker | None = None  # None: the model always picks, in search order
    skip_margin: float = SKIP_MARGIN
    pool: CandidatePool = field(init=False)

    def __post_init__(self) -> None:
        self.pool = CandidatePool(self.catalog, self.search)

    async def match(self, claim: ClaimSpec) -> MatchResult:
        candidates, excluded = await self.pool.covering(claim.indicator_phrase, claim.geo)
        if not candidates:
            return MatchResult(
                status="cant_check",
                indicator_id=None,
                confidence=None,
                reason=f"HoldsUp has no statistics for {place_name(claim.geo)} yet.",
                alternatives=[],
                candidates=[],
                excluded_by_geo=excluded,
            )
        ranked = None
        if self.reranker is not None:
            ranked = await rerank(self.reranker, claim.quote, candidates, self.catalog)
            candidates = ranked.hits
        probabilities = ranked.probabilities if ranked else [None] * len(candidates)
        shown = [
            Candidate(id=h.id, score=h.score, rerank=p)
            for h, p in zip(candidates, probabilities, strict=True)
        ]
        # The model reads the candidates in this order: the reranker's, when it ran.
        run = MatchRun(claim, {h.id: self.catalog.get(h.id) for h in candidates})
        if ranked is not None and ranked.margin >= self.skip_margin:
            result = self._reranker_pick(run, ranked, shown, excluded)
        else:
            answer, convo = await self._ask(run)
            if (nudge := second_look(run, answer)) is not None:
                run.notes.append(nudge.note)
                answer = await self._ask_again(run, convo, answer, nudge.prompt)
            result = self._verdict(run, answer, shown, excluded)
        if ranked is None:
            return result
        return result.model_copy(
            update={"reranker": ranked.model, "margin": round(ranked.margin, 4)}
        )

    def _reranker_pick(
        self, run: MatchRun, ranked: Ranked, shown: list[Candidate], excluded: list[str]
    ) -> MatchResult:
        """The reranker's first candidate, with no model call: its margin is wide enough."""
        spec = run.eligible[ranked.hits[0].id]
        return MatchResult(
            status="matched",
            indicator_id=spec.id,
            confidence="high",
            reason=f"The reranker put {spec.name} well ahead of every other candidate "
            f"(margin {ranked.margin:.2f}), so no model was asked.",
            alternatives=[],
            candidates=shown,
            excluded_by_geo=excluded,
            notes=[
                f"matched by the reranker alone: margin {ranked.margin:.2f} is at least "
                + f"{self.skip_margin:.2f}"
            ],
            skipped_model=True,
        )

    async def _ask_again(
        self,
        run: MatchRun,
        convo: list[ChatCompletionMessageParam],
        answer: MatchAnswer | None,
        nudge: str,
    ) -> MatchAnswer | None:
        """One more turn with `nudge` after the model's first answer."""
        previous = "" if answer is None else answer.model_dump_json()
        result = await self.router.complete(
            "match",
            [
                *convo,
                {"role": "assistant", "content": previous},
                {"role": "user", "content": nudge},
            ],
            use=self.use,
            schema=MatchAnswer,
        )
        run.providers.append(result.provider)
        return result.parsed or answer

    async def _ask(
        self, run: MatchRun
    ) -> tuple[MatchAnswer | None, list[ChatCompletionMessageParam]]:
        convo: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": MATCH_SYSTEM},
            {"role": "user", "content": claim_message(run.claim, list(run.eligible.values()))},
        ]
        while len(run.tool_calls) < MAX_TOOL_CALLS:
            result = await self.router.complete("match", convo, use=self.use, tools=TOOLS)
            run.providers.append(result.provider)
            if not result.tool_calls:
                if (answer := parse_answer(result.content)) is not None:
                    return answer, convo
                convo.append({"role": "assistant", "content": result.content or ""})
                break
            convo.append(tool_calls_message(result.tool_calls))
            for call in result.tool_calls:
                convo.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": await answer_tool_call(self.pool, run, call),
                    }
                )
        final = await self.router.complete(
            "match", [*convo, {"role": "user", "content": FINAL_PROMPT}], use=self.use,
            schema=MatchAnswer,
        )  # fmt: skip
        run.providers.append(final.provider)
        return final.parsed, convo

    def _verdict(
        self,
        run: MatchRun,
        answer: MatchAnswer | None,
        shown: list[Candidate],
        excluded: list[str],
    ) -> MatchResult:
        notes: list[str] = list(run.notes)
        picked = None if answer is None else answer.indicator_id
        if picked is not None and picked not in run.eligible:
            notes.append(f"model picked {picked!r}, which it was not shown for this place")
            picked = None
        alternatives = []
        for alt in [] if answer is None else answer.alternatives:
            if alt in run.eligible and alt != picked and alt not in alternatives:
                alternatives.append(alt)
        confidence = None if answer is None else answer.confidence
        reason = "No answer." if answer is None else answer.reason
        if picked is not None and confidence == "low":
            notes.append(f"model picked {picked!r} with low confidence")
            alternatives.insert(0, picked)
            picked = None
        return MatchResult(
            status="matched" if picked is not None else "cant_check",
            indicator_id=picked,
            confidence=confidence,
            reason=reason,
            alternatives=alternatives[:MAX_ALTERNATIVES],
            candidates=shown,
            excluded_by_geo=excluded,
            tool_calls=run.tool_calls,
            providers=run.providers,
            notes=notes,
        )
