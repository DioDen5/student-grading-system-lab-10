from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from grade_service.api import create_app
from grade_service.database import create_schema, create_sqlite_engine, make_session_factory


@pytest.fixture
def engine(tmp_path) -> Iterator[Engine]:
    engine = create_sqlite_engine(tmp_path / "test.db")
    create_schema(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    factory = make_session_factory(engine)
    with factory() as session:
        yield session


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    app = create_app(tmp_path / "api-test.db")
    with TestClient(app) as client:
        yield client
    app.state.engine.dispose()
