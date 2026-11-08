import httpx

from holdsup.adapters.registry import ADAPTER_FACTORIES, build_adapters


async def test_each_adapter_is_keyed_by_its_own_source() -> None:
    async with httpx.AsyncClient() as http:
        adapters = build_adapters(http)
    assert set(adapters) == {str(s) for s in ADAPTER_FACTORIES}
    for name, adapter in adapters.items():
        assert adapter.source == name
