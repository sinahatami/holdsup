"""The live trace: one `StepEvent` when a step starts and one when it is done.

`Trace` times each step and hands its events to `emit` (the service publishes them on the
check's event stream, and the result page draws them as the trace).
"""

import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Step(StrEnum):
    LEDGER = "ledger"
    EXTRACT = "extract"
    MATCH = "match"
    FETCH = "fetch"
    PLAN = "plan"
    EXECUTE = "execute"
    VERDICT = "verdict"
    EXPLAIN = "explain"


StepStatus = Literal["ok", "cant_check"]


class StepEvent(BaseModel):
    """One line of the live trace."""

    event: Literal["step_started", "step_done"]
    step: Step
    claim: int | None = None  # which extracted claim; None for check-wide steps
    status: StepStatus | None = None  # step_done only
    summary: str = ""
    models: list[str] = Field(default_factory=list)  # "provider/model" per model call
    ms: float | None = None  # step_done only


class ModelUse(BaseModel):
    """One model call a step made."""

    step: Step
    provider: str
    model: str


Emit = Callable[[StepEvent], Awaitable[None]]


@dataclass
class Trace:
    emit: Emit
    started: dict[tuple[Step, int | None], float] = field(default_factory=dict)

    async def start(self, step: Step, claim: int | None = None) -> None:
        self.started[step, claim] = time.monotonic()
        await self.emit(StepEvent(event="step_started", step=step, claim=claim))

    async def done(
        self,
        step: Step,
        claim: int | None,
        summary: str,
        *,
        status: StepStatus = "ok",
        models: Sequence[ModelUse] = (),
    ) -> None:
        began = self.started.pop((step, claim), time.monotonic())
        await self.emit(
            StepEvent(
                event="step_done",
                step=step,
                claim=claim,
                status=status,
                summary=summary,
                models=[f"{m.provider}/{m.model}" for m in models],
                ms=round((time.monotonic() - began) * 1000, 1),
            )
        )
