import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-with-at-least-thirty-two-characters"
os.environ["BOOTSTRAP_PASSWORD"] = "deterministic-test-password"
os.environ["DATA_ROOT"] = str(Path(__file__).resolve().parents[2] / "data")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.seed import seed  # noqa: E402


@pytest.fixture(scope="session")
def seeded_snapshot():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(engine).begin() as db:
        seed(db)
    # Snapshot is copied per test, keeping GX suite execution fast and tests isolated.
    with engine.connect() as connection:
        return "\n".join(connection.connection.driver_connection.iterdump())


@pytest.fixture
def client(seeded_snapshot):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with engine.connect() as connection:
        connection.connection.driver_connection.executescript(seeded_snapshot)
        connection.connection.driver_connection.execute("PRAGMA foreign_keys=ON")
    sessions = sessionmaker(engine, expire_on_commit=False)

    def override():
        with sessions() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[get_db] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def auth(client):
    def headers(role="governance_analyst"):
        response = client.post(
            "/api/auth/login",
            json={"email": f"{role}@example.test", "password": os.environ["BOOTSTRAP_PASSWORD"]},
        )
        assert response.status_code == 200
        return {"Authorization": f'Bearer {response.json()["access_token"]}'}

    return headers
