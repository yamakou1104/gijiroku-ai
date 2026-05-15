import importlib
from unittest.mock import patch, MagicMock


def test_notify_calls_plyer():
    mock_plyer_notify = MagicMock()
    mock_notification = MagicMock()
    mock_notification.notify = mock_plyer_notify
    mock_plyer = MagicMock()
    mock_plyer.notification = mock_notification

    with patch.dict("sys.modules", {"plyer": mock_plyer, "plyer.notification": mock_notification}):
        import utils.notification
        importlib.reload(utils.notification)
        utils.notification.notify("タイトル", "メッセージ")
        mock_plyer_notify.assert_called_once()


def test_notify_handles_import_error(caplog):
    with patch.dict("sys.modules", {"plyer": None, "plyer.notification": None}):
        import utils.notification
        importlib.reload(utils.notification)
        with caplog.at_level("INFO"):
            utils.notification.notify("タイトル", "メッセージ")
        assert "タイトル" in caplog.text


def test_notify_handles_runtime_error(caplog):
    mock_notification = MagicMock()
    mock_notification.notify.side_effect = RuntimeError("no backend")
    mock_plyer = MagicMock()
    mock_plyer.notification = mock_notification

    with patch.dict("sys.modules", {"plyer": mock_plyer, "plyer.notification": mock_notification}):
        import utils.notification
        importlib.reload(utils.notification)
        with caplog.at_level("INFO"):
            utils.notification.notify("タイトル", "メッセージ")
        assert "タイトル" in caplog.text
