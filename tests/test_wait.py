import pytest

from baseapp.wait import wait_for_commit


def test_returns_when_commit_matches():
    seen = iter([{"commit": "old"}, {"commit": "new"}])
    assert wait_for_commit("http://a", "new", interval=0, fetch=lambda u: next(seen)) >= 0


def test_tolerates_unreachable_while_rolling_out():
    calls = iter([OSError("refused"), {"commit": "new"}])

    def fetch(u):
        r = next(calls)
        if isinstance(r, Exception):
            raise r
        return r
    wait_for_commit("http://a", "new", interval=0, fetch=fetch)


def test_times_out_with_what_it_saw():
    with pytest.raises(TimeoutError, match="still reports old after"):
        wait_for_commit("http://a", "new", timeout=0.01, interval=0, fetch=lambda u: {"commit": "old"})
