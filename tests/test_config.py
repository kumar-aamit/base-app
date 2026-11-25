from pathlib import Path

from baseapp.config import Settings


def test_defaults():
    s = Settings.from_env({})
    assert s.app_dir == Path("/opt/app-root/app")
    assert s.port == 8742 and s.commit == "dev" and s.site_name == "dCloud lab"
    assert s.mock is False and s.api_key is None
    assert not s.fast.configured and not s.smart.configured


def test_reads_endpoints_and_strips_trailing_slash():
    s = Settings.from_env({
        "LLM_SMART_URL": "http://nemotron-super.models.svc:8000/v1/",
        "LLM_SMART_MODEL": "nvidia/nemotron-3.5-super",
        "LLM_MOCK": "1", "LLM_API_KEY": "", "APP_COMMIT": "abc123",
    })
    assert s.smart.url == "http://nemotron-super.models.svc:8000/v1"
    assert s.smart.configured and s.mock is True
    assert s.api_key is None and s.commit == "abc123"
