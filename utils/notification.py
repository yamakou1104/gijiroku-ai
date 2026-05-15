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
        print(f"[通知] {title}: {message}")
