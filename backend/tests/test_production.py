import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app import auth, security
from app.config import settings
from app.db import Base
from app.models import StaffUser
from app.manage import create_admin
from app.seed import SCHEMA_VERSION, init_db


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "secret_key", "production-test-key-" * 4)
    monkeypatch.setattr(settings, "show_demo_accounts", False)
    monkeypatch.setattr(settings, "seed_on_startup", False)
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "cors_origins", "https://example.com")


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    sessions = sessionmaker(bind=engine)
    yield engine, sessions
    engine.dispose()


@pytest.mark.parametrize("name,value,message", [
    ("auth_enabled", False, "AUTH_ENABLED"),
    ("seed_on_startup", True, "SEED_ON_STARTUP"),
    ("rate_limit_enabled", False, "RATE_LIMIT_ENABLED"),
    ("cors_origins", "*", "CORS_ORIGINS"),
    ("cors_origins", "http://example.com", "CORS_ORIGINS"),
    ("cors_origins", "https://example.com, http://localhost:3000", "CORS_ORIGINS"),
    ("cors_origins", "https://example.com/path", "CORS_ORIGINS"),
    ("cors_origins", "https://user:password@example.com", "CORS_ORIGINS"),
    ("cors_origins", "https://", "CORS_ORIGINS"),
    ("cors_origins", "", "CORS_ORIGINS"),
])
def test_production_rejects_unsafe_settings(production, monkeypatch, name, value, message):
    monkeypatch.setattr(settings, name, value)
    with pytest.raises(RuntimeError, match=message):
        security.check_production_config()


def test_production_accepts_explicit_https_origins(production, monkeypatch):
    monkeypatch.setattr(settings, "cors_origins", "https://example.com, https://staff.example.com:8443")
    security.check_production_config()


def test_production_rejects_demo_seed_before_creating_tables(production, database):
    engine, sessions = database
    with pytest.raises(RuntimeError, match="SEED_ON_STARTUP"):
        init_db(seed_if_empty=True, bind=engine, session_factory=sessions)
    assert inspect(engine).get_table_names() == []


@pytest.mark.parametrize("environment,seed_if_empty", [("production", False), ("development", False)])
@pytest.mark.parametrize("has_meta", [True, False])
def test_schema_mismatch_preserves_existing_data(database, monkeypatch, environment, seed_if_empty, has_meta):
    engine, sessions = database
    monkeypatch.setattr(settings, "environment", environment)
    Base.metadata.create_all(engine)
    with sessions() as session:
        session.add(StaffUser(username="real-staff", password_hash="stored-hash", role="admin", is_demo=False))
        session.commit()
    with engine.begin() as connection:
        if has_meta:
            connection.execute(text("CREATE TABLE app_meta (key VARCHAR(40) PRIMARY KEY, value VARCHAR(40))"))
            connection.execute(text("INSERT INTO app_meta VALUES ('schema_version', 'old')"))
    with pytest.raises(RuntimeError, match="migratsiya"):
        init_db(seed_if_empty=seed_if_empty, bind=engine, session_factory=sessions)
    with sessions() as session:
        assert session.query(StaffUser).one().username == "real-staff"
    if has_meta:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT value FROM app_meta")).scalar_one() == "old"
    else:
        assert "app_meta" not in inspect(engine).get_table_names()


def test_fresh_production_database_has_no_demo_users(production, database):
    engine, sessions = database
    init_db(seed_if_empty=False, bind=engine, session_factory=sessions)
    init_db(seed_if_empty=False, bind=engine, session_factory=sessions)
    with sessions() as session:
        auth.seed_users(session)
        assert session.query(StaffUser).count() == 0
    with engine.connect() as connection:
        assert connection.execute(text("SELECT value FROM app_meta")).scalar_one() == SCHEMA_VERSION


def test_production_blocks_demo_login_and_existing_demo_token(client, monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "production-test-key-" * 4)
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    token = response.json()["token"]
    monkeypatch.setattr(settings, "environment", "production")
    assert client.post("/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 401
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert client.get("/inspector/alerts", headers=headers).status_code == 401


def test_production_hides_demo_accounts_even_if_misconfigured(client, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "show_demo_accounts", True)
    assert client.get("/auth/demo-accounts").json() == []


def test_production_never_bypasses_auth(production, monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", False)
    with pytest.raises(HTTPException) as error:
        auth.require_role("inspector")(None)
    assert error.value.status_code == 401


def test_production_requires_explicit_signing_key(production, monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        auth._secret()


def test_production_uses_current_staff_role_and_rejects_deleted_user(production, database):
    engine, sessions = database
    Base.metadata.create_all(engine)
    with sessions() as session:
        user = StaffUser(username="real-staff", password_hash=auth.hash_password("a-long-test-password"),
                         role="admin", is_demo=False)
        session.add(user)
        session.commit()
        header = f"Bearer {auth.make_token(user)}"
        assert auth.current_user(header, session)["r"] == "admin"
        user.role = "inspector"
        session.commit()
        assert auth.current_user(header, session)["r"] == "inspector"
        session.delete(user)
        session.commit()
        assert auth.current_user(header, session) is None


def test_create_real_admin_and_login(production, database):
    engine, sessions = database
    Base.metadata.create_all(engine)
    with sessions() as session:
        user = create_admin(session, " Operator ", "a-long-unique-password")
        assert user.username == "operator"
        assert user.role == "admin" and not user.is_demo
        assert user.password_hash != "a-long-unique-password"
        response = auth.login(auth.LoginRequest(username="operator", password="a-long-unique-password"), session)
        assert auth.current_user(f"Bearer {response.token}", session)["u"] == "operator"
        with pytest.raises(ValueError, match="mavjud"):
            create_admin(session, "operator", "a-different-long-password")
        assert auth.check_password("a-long-unique-password", user.password_hash)
        assert session.query(StaffUser).count() == 1


@pytest.mark.parametrize("username,password", [
    ("ab", "a-long-unique-password"),
    ("bad user", "a-long-unique-password"),
    ("operator", "admin123"),
    ("operator", " " * 16),
])
def test_admin_validation_does_not_create_user(database, username, password):
    engine, sessions = database
    Base.metadata.create_all(engine)
    with sessions() as session:
        with pytest.raises(ValueError):
            create_admin(session, username, password)
        assert session.query(StaffUser).count() == 0
