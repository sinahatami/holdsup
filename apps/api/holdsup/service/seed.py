"""Seed the gallery: run curated claims through the real runner and feature the good results."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from holdsup.problems import ProblemError
from holdsup.service.runner import CheckRunner
from holdsup.service.store import CheckResult, CheckStatus, CheckStore
from holdsup.verdict import Label

SEED_CLIENT = "gallery-seed"
RETIRE_SCAN = 1000  # featured checks looked at for earlier copies of the curated claims


@dataclass(frozen=True)
class SeedOutcome:
    text: str
    check_id: UUID | None
    featured: bool
    note: str  # why a claim was not featured, or the verdicts when it was
    verdicts: tuple[Label, ...] = ()


def read_claims(path: Path) -> list[str]:
    """One claim per line; blank lines and lines starting with # are ignored."""
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def _unfit(result: CheckResult) -> str | None:
    """Why a result should not be shown in the gallery, or None."""
    if not result.claims:
        return "no claim found"
    if any(c.retryable for c in result.claims):
        return "a source or model failed (retryable)"
    if all(c.verdict.label is Label.CANT_CHECK for c in result.claims):
        return "can't check"
    return None


async def seed_gallery(
    runner: CheckRunner, store: CheckStore, claims: Sequence[str]
) -> list[SeedOutcome]:
    """Check the claims one after another (to respect provider limits) and feature good results.

    Reruns are cheap: a claim checked before comes back from the ledger with no model call.
    Earlier featured checks of the same claims are taken out of the gallery, so a rerun after a
    fix replaces old verdicts instead of showing both.
    """
    outcomes: list[SeedOutcome] = []
    for text in claims:
        try:
            submitted = await runner.submit(text, SEED_CLIENT)
        except ProblemError as err:
            outcomes.append(SeedOutcome(text, None, False, err.problem.title))
            continue
        async for _ in runner.events(submitted.id):  # wait for the run to end
            pass
        stored = await store.get(submitted.id)
        if stored is None or stored.status is not CheckStatus.DONE or stored.result is None:
            reason = stored.error.get("title", "failed") if stored and stored.error else "failed"
            outcomes.append(SeedOutcome(text, submitted.id, False, str(reason)))
            continue
        result = CheckResult.model_validate(stored.result)
        verdicts = tuple(c.verdict.label for c in result.claims)
        unfit = _unfit(result)
        if unfit is not None:
            outcomes.append(SeedOutcome(text, submitted.id, False, unfit, verdicts))
            continue
        await store.set_featured(submitted.id, True)
        outcomes.append(SeedOutcome(text, submitted.id, True, "featured", verdicts))
    await retire_earlier(store, outcomes)
    return outcomes


async def retire_earlier(store: CheckStore, outcomes: Sequence[SeedOutcome]) -> list[UUID]:
    """Unfeature featured checks of these claims other than the ones this run just checked."""
    texts = {o.text for o in outcomes}
    current = {o.check_id for o in outcomes}
    retired = [
        c.id for c in await store.gallery(RETIRE_SCAN) if c.text in texts and c.id not in current
    ]
    for check_id in retired:
        await store.set_featured(check_id, False)
    return retired


def format_table(outcomes: Sequence[SeedOutcome]) -> str:
    rows = [
        f"{'yes' if o.featured else 'NO ':3}  {', '.join(o.verdicts) or '-':32}  "
        f"{o.note:36}  {o.text[:70]}"
        for o in outcomes
    ]
    done = sum(o.featured for o in outcomes)
    return "\n".join([*rows, f"{done}/{len(outcomes)} claims featured"])
