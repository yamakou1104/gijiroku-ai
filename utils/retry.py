import time
import logging

logger = logging.getLogger(__name__)


def retry(func, max_retries=3, initial_delay=2, backoff_factor=2,
          max_delay=60, retryable_exceptions=(Exception,)):
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            return func()
        except retryable_exceptions as e:
            if attempt == max_retries:
                logger.error("All %d retries exhausted: %s", max_retries, e)
                raise
            logger.warning(
                "Attempt %d/%d failed: %s. Retrying in %ds...",
                attempt + 1, max_retries, e, delay,
            )
            time.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)
