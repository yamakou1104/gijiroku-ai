import logging

logger = logging.getLogger(__name__)


def notify(title, message, timeout=10):
    try:
        from plyer import notification as plyer_notification

        plyer_notification.notify(
            title=title,
            message=message,
            app_name="議事録AI",
            timeout=timeout,
        )
    except Exception:
        logger.info("[通知] %s: %s", title, message)
