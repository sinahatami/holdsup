"""JSON data as Python types."""

from typing import Any

# A JSON object whose shape is owned elsewhere: a stored CheckResult, an SSE event's payload,
# a model's tool arguments. Any, because each value's type is set by the schema that wrote it
# (a Pydantic model or a tool's JSON schema); code reads typed fields through that schema.
JsonObject = dict[str, Any]
