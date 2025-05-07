import pytest

from idum_proxy.idum_proxy import IdumProxy


@pytest.mark.asyncio
async def test_load_config():
    idum_proxy = IdumProxy(config_file="idum_proxy/default.json")
    assert idum_proxy.config.name == "Idum Proxy"
