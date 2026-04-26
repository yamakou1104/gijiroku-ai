from plyer import notification as plyer_notification


def notify(title, message, timeout=10):
    plyer_notification.notify(
        title=title,
        message=message,
        app_name="議事録AI",
        timeout=timeout,
    )
