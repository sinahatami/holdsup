from datetime import UTC, datetime
from uuid import uuid4

from holdsup.service.removal import PREVIEW_CHARS, describe, remove_check
from holdsup.service.store import CheckStatus, InMemoryCheckStore, StoredCheck

T0 = datetime(2026, 11, 21, 9, 5, tzinfo=UTC)


def a_check(text: str) -> StoredCheck:
    return StoredCheck(uuid4(), text, CheckStatus.DONE, T0)


def test_describe_shows_when_and_the_text_on_one_indented_line() -> None:
    check = a_check("Mario Rossi said\n\nunemployment is 7%.")
    assert describe(check) == (
        f"Check {check.id}, 2026-11-21 09:05 UTC\n  Mario Rossi said unemployment is 7%.\n"
    )
    long = describe(a_check("x" * (PREVIEW_CHARS + 50)))
    assert long.endswith("x" * PREVIEW_CHARS + "…\n")


async def test_nothing_is_deleted_without_a_yes() -> None:
    store = InMemoryCheckStore()
    check = a_check("A claim with a name in it.")
    await store.create(check)
    seen: list[str] = []

    def refuse(description: str) -> bool:
        seen.append(description)
        return False

    assert await remove_check(store, check.id, refuse) == "Nothing deleted.\n"
    assert seen == [describe(check)]
    assert await store.get(check.id) is not None


async def test_a_yes_deletes_the_check_and_its_copies() -> None:
    store = InMemoryCheckStore()
    check, twin, other = a_check("Same text."), a_check("Same text."), a_check("Other.")
    for c in (check, twin, other):
        await store.create(c)
    message = await remove_check(store, check.id, lambda _: True)
    assert message.startswith("Deleted 2 checks of this text:\n")
    assert f"  {check.id}\n" in message and f"  {twin.id}\n" in message
    assert set(store.checks) == {other.id}


async def test_an_unknown_check_is_said_so() -> None:
    unknown = uuid4()
    assert await remove_check(InMemoryCheckStore(), unknown, lambda _: True) == (
        f"No check {unknown}.\n"
    )
