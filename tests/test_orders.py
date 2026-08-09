from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app

client = TestClient(app)


def override_get_db(mock_db):
    def _override():
        yield mock_db
    return _override


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.orders.release_lock")
@patch("app.orders.acquire_lock")
def test_checkout_lock_conflict(mock_acquire_lock, mock_release_lock):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_acquire_lock.return_value = False

    app.dependency_overrides[get_db] = override_get_db(mock_db)
    try:
        payload = {
            "customer_email": "test@example.com",
            "idempotency_key": "dup-key",
            "items": [{"product_name": "Widget", "quantity": 1, "unit_price": 9.99}],
        }
        response = client.post("/orders/checkout", json=payload)
        assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()


@patch("app.orders.release_lock")
@patch("app.orders.acquire_lock")
def test_checkout_idempotent_replay(mock_acquire_lock, mock_release_lock):
    mock_db = MagicMock()
    existing_order = MagicMock(id=1, status="confirmed")
    mock_db.query.return_value.filter.return_value.first.return_value = existing_order

    app.dependency_overrides[get_db] = override_get_db(mock_db)
    try:
        payload = {
            "customer_email": "test@example.com",
            "idempotency_key": "existing-key",
            "items": [{"product_name": "Widget", "quantity": 1, "unit_price": 9.99}],
        }
        response = client.post("/orders/checkout", json=payload)
        assert response.status_code == 200
        assert response.json() == {"order_id": 1, "status": "confirmed"}
        mock_acquire_lock.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@patch("app.orders.release_lock")
@patch("app.orders.acquire_lock")
def test_checkout_success(mock_acquire_lock, mock_release_lock):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_acquire_lock.return_value = True

    def fake_refresh(order):
        order.id = 42
        order.status = "confirmed"

    mock_db.refresh.side_effect = fake_refresh

    app.dependency_overrides[get_db] = override_get_db(mock_db)
    try:
        payload = {
            "customer_email": "test@example.com",
            "idempotency_key": "new-key",
            "items": [{"product_name": "Widget", "quantity": 2, "unit_price": 5.0}],
        }
        response = client.post("/orders/checkout", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["order_id"] == 42
        assert body["status"] == "confirmed"
        mock_release_lock.assert_called_once_with("new-key")
    finally:
        app.dependency_overrides.clear()


def test_get_order_found():
    mock_db = MagicMock()
    mock_order = MagicMock(
        id=7, status="confirmed", total_amount=19.98, customer_email="a@b.com"
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_order

    app.dependency_overrides[get_db] = override_get_db(mock_db)
    try:
        response = client.get("/orders/7")
        assert response.status_code == 200
        assert response.json() == {
            "order_id": 7,
            "status": "confirmed",
            "total_amount": 19.98,
            "customer_email": "a@b.com",
        }
    finally:
        app.dependency_overrides.clear()


def test_get_order_not_found():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_db] = override_get_db(mock_db)
    try:
        response = client.get("/orders/99999")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_get_db_yields_and_closes_session():
    with patch("app.db.SessionLocal") as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        gen = get_db()
        db = next(gen)
        assert db is mock_session

        try:
            next(gen)
        except StopIteration:
            pass

        mock_session.close.assert_called_once()


def test_lifespan_creates_tables():
    with patch("app.main.Base") as mock_base:
        with TestClient(app) as lifespan_client:
            lifespan_client.get("/health")
        mock_base.metadata.create_all.assert_called_once()
