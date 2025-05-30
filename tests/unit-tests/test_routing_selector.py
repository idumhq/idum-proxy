import pytest

from idum_proxy import IdumProxy


@pytest.mark.asyncio
async def test_routing_selector_valid():
    idum_proxy = IdumProxy(config_file="idum_proxy/default.json")

    paths = [
        "/github-api",
        "/github-api/",
        "/github-api/demo",
        "/github-api/demo/demo",
        "/github-api/demo/demo/demo",
        "/github-api/demo/demo/demo/demo",
    ]

    for path in paths:
        assert (
            idum_proxy.routing_selector.find_endpoint(path).backends[0].https[0].url
            == "https://api.github.com"
        )


@pytest.mark.asyncio
async def test_routing_selector_invalid():
    idum_proxy = IdumProxy(config_file="idum_proxy/default.json")

    star_paths = ["", "/", "unknown"]

    for path in star_paths:
        assert (
            idum_proxy.routing_selector.find_endpoint(path).backends[0].https
            is not None
        )
        assert (
            idum_proxy.routing_selector.find_endpoint(path).backends[0].https.url
            == "https://sandbox.api.service.nhs.uk/hello-world/hello/world$"
        )
