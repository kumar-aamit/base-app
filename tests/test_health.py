import asyncio

import httpx

from baseapp.config import ModelEndpoint, Settings
from baseapp.health import check_model, run_checks

EP = ModelEndpoint("http://m:8000/v1", "nvidia/nemotron-3.5-super")


def run(handler, ep=EP, key=None):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await check_model("Smart model", ep, key, c)
    return asyncio.run(go())


def test_ok_when_model_is_served():
    r = run(lambda req: httpx.Response(200, json={"data": [{"id": EP.model}]}))
    assert r.ok and r.detail == "nvidia/nemotron-3.5-super answered" and r.ms is not None


def test_wrong_model_name():
    r = run(lambda req: httpx.Response(200, json={"data": [{"id": "other"}]}))
    assert not r.ok and r.detail == "model nvidia/nemotron-3.5-super not served"


def test_http_error():
    assert run(lambda req: httpx.Response(503)).detail == "HTTP 503"


def test_timeout():
    def boom(req):
        raise httpx.ReadTimeout("slow", request=req)
    assert run(boom).detail == "timeout after 3 s"


def test_not_configured_sends_nothing():
    def fail(req):
        raise AssertionError("no request expected")
    assert run(fail, ep=ModelEndpoint("", "")).detail == "not configured"


def test_auth_header_only_with_key():
    seen = {}

    def h(req):
        seen["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json={"data": [{"id": EP.model}]})
    run(h)
    assert seen["auth"] is None
    run(h, key="k")
    assert seen["auth"] == "Bearer k"


def test_mock_mode_skips_requests():
    s = Settings.from_env({"LLM_MOCK": "1"})

    def fail(req):
        raise AssertionError("no request expected")

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as c:
            return await run_checks(s, c)
    results = asyncio.run(go())
    assert [r.name for r in results] == ["Fast model", "Smart model"]
    assert all(r.ok and r.detail == "mock mode" for r in results)
