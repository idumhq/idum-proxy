"""
import pytest

from idum_proxy.idum_proxy import _forge_target_url


@pytest.mark.asyncio
async def test__forge_target_url():
    url = "http://fake-url.com"

    assert await _forge_target_url(url="test", path="", prefix="") == "test"
    assert await _forge_target_url(url="/", path="", prefix="") == ""
    assert await _forge_target_url(url="", path="", prefix="") == ""
    assert (
        await _forge_target_url(url=url, path="/path/", prefix="prefix")
        == f"{url}/path"
    )
    assert (
        await _forge_target_url(url=url, path="prefixpath/", prefix="prefix")
        == f"{url}/path"
    )

"""
