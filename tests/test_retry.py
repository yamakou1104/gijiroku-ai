"""Tests for utils.retry module."""

from unittest.mock import patch, MagicMock

import pytest

from utils.retry import retry


# ---------------------------------------------------------------------------
# 1. Basic success -- function succeeds on first try, no retry needed
# ---------------------------------------------------------------------------

@patch("utils.retry.time.sleep")
def test_basic_success_no_retry(mock_sleep):
    func = MagicMock(return_value="ok")

    result = retry(func)

    assert result == "ok"
    func.assert_called_once()
    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# 2. Retry then success -- function fails N times then succeeds
# ---------------------------------------------------------------------------

@patch("utils.retry.time.sleep")
def test_retry_then_success(mock_sleep):
    func = MagicMock(side_effect=[ValueError("err1"), ValueError("err2"), "success"])

    result = retry(func, max_retries=3, initial_delay=1, backoff_factor=2)

    assert result == "success"
    assert func.call_count == 3
    # Two failures -> two sleeps
    assert mock_sleep.call_count == 2


# ---------------------------------------------------------------------------
# 3. Max retries exhausted -- function fails every time, raises last exception
# ---------------------------------------------------------------------------

@patch("utils.retry.time.sleep")
def test_max_retries_exhausted(mock_sleep):
    func = MagicMock(side_effect=RuntimeError("persistent failure"))

    with pytest.raises(RuntimeError, match="persistent failure"):
        retry(func, max_retries=2, initial_delay=1)

    # 1 initial attempt + 2 retries = 3 calls
    assert func.call_count == 3
    # 2 sleeps (after attempt 0 and attempt 1; attempt 2 is the last so no sleep)
    assert mock_sleep.call_count == 2


# ---------------------------------------------------------------------------
# 4. Backoff timing -- verify delays increase exponentially (mock time.sleep)
# ---------------------------------------------------------------------------

@patch("utils.retry.time.sleep")
def test_backoff_timing(mock_sleep):
    func = MagicMock(side_effect=[OSError("e")] * 4 + ["done"])

    result = retry(
        func,
        max_retries=5,
        initial_delay=1,
        backoff_factor=2,
        max_delay=100,
    )

    assert result == "done"
    # Delays: 1, 2, 4, 8
    sleep_delays = [call.args[0] for call in mock_sleep.call_args_list]
    assert sleep_delays == [1, 2, 4, 8]


# ---------------------------------------------------------------------------
# 5. Max delay cap -- delay doesn't exceed max_delay parameter
# ---------------------------------------------------------------------------

@patch("utils.retry.time.sleep")
def test_max_delay_cap(mock_sleep):
    func = MagicMock(side_effect=[IOError("e")] * 5 + ["ok"])

    retry(
        func,
        max_retries=6,
        initial_delay=10,
        backoff_factor=3,
        max_delay=50,
    )

    sleep_delays = [call.args[0] for call in mock_sleep.call_args_list]
    # Expected: 10, 30, 50 (capped), 50, 50
    assert sleep_delays == [10, 30, 50, 50, 50]


# ---------------------------------------------------------------------------
# 6. Retryable exceptions filter -- only specified types trigger retry
# ---------------------------------------------------------------------------

@patch("utils.retry.time.sleep")
def test_retryable_exceptions_filter(mock_sleep):
    func = MagicMock(
        side_effect=[ConnectionError("net"), ConnectionError("net"), "connected"]
    )

    result = retry(
        func,
        max_retries=3,
        initial_delay=1,
        retryable_exceptions=(ConnectionError,),
    )

    assert result == "connected"
    assert func.call_count == 3
    assert mock_sleep.call_count == 2


# ---------------------------------------------------------------------------
# 7. Non-retryable exception -- raises immediately without retry
# ---------------------------------------------------------------------------

@patch("utils.retry.time.sleep")
def test_non_retryable_exception_propagates_immediately(mock_sleep):
    func = MagicMock(side_effect=TypeError("bad type"))

    with pytest.raises(TypeError, match="bad type"):
        retry(func, max_retries=5, retryable_exceptions=(ConnectionError, IOError))

    # Should have been called only once -- no retry attempted
    func.assert_called_once()
    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# 8. Default parameters -- retry works with default arguments
# ---------------------------------------------------------------------------

@patch("utils.retry.time.sleep")
def test_default_parameters(mock_sleep):
    func = MagicMock(side_effect=[Exception("e1"), Exception("e2"), "ok"])

    result = retry(func)

    assert result == "ok"
    assert func.call_count == 3
    # Default initial_delay=2, backoff_factor=2 -> delays: 2, 4
    sleep_delays = [call.args[0] for call in mock_sleep.call_args_list]
    assert sleep_delays == [2, 4]


# ---------------------------------------------------------------------------
# 9. Return value preserved -- the successful call's return value passes through
# ---------------------------------------------------------------------------

@patch("utils.retry.time.sleep")
def test_return_value_preserved(mock_sleep):
    complex_value = {"key": [1, 2, 3], "nested": {"a": True}}
    func = MagicMock(return_value=complex_value)

    result = retry(func)

    assert result is complex_value
