"""Step 5 and 6: the model plans which safe operations to run; code checks and runs them.

The plan never holds a number. The model names operations and their arguments (places,
periods, a change kind); code checks every call against the operation registry and the fetched
data, asks once for a fix when something is wrong, and fills in everything numeric itself: how
far a period may be from the data, unit scales, and the rank order.

Modules, in the order a plan passes through them:
- `model`: the plan and context types.
- `operations`: the registry of operations (signature, year handling, how to run each).
- `repair`, `periods`, `validate`: code's fixes, then checks (`validate_plan`).
- `prompt`: the model call (`plan_analysis`).
- `execute`: running a valid plan (`execute_plan`).
"""

from holdsup.pipeline.plan.execute import Execution, execute_plan
from holdsup.pipeline.plan.model import (
    MAX_CALLS,
    ModelPlan,
    OpCall,
    OpName,
    PlanContext,
    PlanInvalid,
    SeriesInfo,
    ValidPlan,
)
from holdsup.pipeline.plan.operations import (
    OPERATIONS,
    SERIES_OPS,
    SIGNATURES,
    OpSpec,
    per_person_unit,
)
from holdsup.pipeline.plan.periods import claim_years, yearly_allowed
from holdsup.pipeline.plan.prompt import PLAN_SYSTEM, PlanResult, plan_analysis, plan_message
from holdsup.pipeline.plan.validate import validate_plan

__all__ = [
    "MAX_CALLS",
    "OPERATIONS",
    "PLAN_SYSTEM",
    "SERIES_OPS",
    "SIGNATURES",
    "Execution",
    "ModelPlan",
    "OpCall",
    "OpName",
    "OpSpec",
    "PlanContext",
    "PlanInvalid",
    "PlanResult",
    "SeriesInfo",
    "ValidPlan",
    "claim_years",
    "execute_plan",
    "per_person_unit",
    "plan_analysis",
    "plan_message",
    "validate_plan",
    "yearly_allowed",
]
