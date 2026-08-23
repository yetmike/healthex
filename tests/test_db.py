"""Tests for db.make_engine — engine/pool reuse."""

from healthex.db import make_engine


def test_same_url_reuses_one_engine(db_url: str) -> None:
    """A new Engine per call means a new connection pool per call, never disposed."""
    assert make_engine(db_url) is make_engine(db_url)


def test_different_urls_get_different_engines(db_url: str) -> None:
    other = db_url + "?application_name=other"
    assert make_engine(db_url) is not make_engine(other)


def test_sessions_share_the_cached_engine(db_url: str) -> None:
    from healthex.db import make_session_factory

    a = make_session_factory(db_url)
    b = make_session_factory(db_url)
    assert a.kw["bind"] is b.kw["bind"]
