from unittest.mock import patch, MagicMock

from app.cache import acquire_lock, release_lock, check_lock


@patch("app.cache.redis_client")
def test_acquire_lock_success(mock_redis):
    mock_redis.set.return_value = True
    result = acquire_lock("order-123")
    assert result is True
    mock_redis.set.assert_called_once_with(
        "checkout_lock:order-123", "locked", nx=True, ex=30
    )


@patch("app.cache.redis_client")
def test_acquire_lock_already_held(mock_redis):
    mock_redis.set.return_value = None
    result = acquire_lock("order-123")
    assert result is False


@patch("app.cache.redis_client")
def test_release_lock(mock_redis):
    release_lock("order-123")
    mock_redis.delete.assert_called_once_with("checkout_lock:order-123")


@patch("app.cache.redis_client")
def test_check_lock_present(mock_redis):
    mock_redis.get.return_value = "locked"
    assert check_lock("order-123") is True


@patch("app.cache.redis_client")
def test_check_lock_absent(mock_redis):
    mock_redis.get.return_value = None
    assert check_lock("order-123") is False
