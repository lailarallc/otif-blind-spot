"""The prod guard sits in front of the pipeline's Postgres read.

`scripts/00_query_cinderhaven.py` reads DATABASE_URL, which in local use is
localhost:5432 -- a `fly proxy` tunnel to production when one is open.
This test fakes a flyctl listener and asserts nothing connects.
"""

import importlib.util
import pathlib
import sys

import pytest

SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"


@pytest.fixture
def query_module(monkeypatch):
    try:
        import dotenv
        monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **kw: None)  # keep .env out
    except ImportError:
        pass
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:5432/db")
    monkeypatch.delenv("ALLOW_PROD_DB", raising=False)
    monkeypatch.syspath_prepend(str(SCRIPTS))
    monkeypatch.delitem(sys.modules, "otif_config", raising=False)
    spec = importlib.util.spec_from_file_location("otif_query", SCRIPTS / "00_query_cinderhaven.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_get_conn_refuses_fly_tunnel(query_module, monkeypatch):
    monkeypatch.setattr(query_module.prod_guard, "_listener", lambda port: "flyctl")
    monkeypatch.setattr(query_module.psycopg2, "connect", lambda *a, **kw: pytest.fail("connected"))
    with pytest.raises(query_module.prod_guard.ProdDatabaseError):
        query_module.get_conn()
