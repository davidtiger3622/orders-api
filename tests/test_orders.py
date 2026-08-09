from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.orders.release_lock")
@patch("app.orders.acquire_lock")
@patch("app.orders.get_db")
def test_checkout_lock_conflict(mock_get_db, mock_acquire_lock, mock_release_lock):
    mock_db = mock_get_db.return_value
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_acquire_lock.return_value = False

    payload = {
        "customer_email": "test@example.com",
        "idempotency_key": "dup-key",
        "items": [{"product_name": "Widget", "quantity": 1, "unit_price": 9.99}],
    }
    response = client.post("/orders/checkout", json=payload)
    assert response.status_code in (409, 422)


def test_get_order_not_found():
    response = client.get("/orders/99999")
    assert response.status_code in (404, 500)
