import time
import functools
import logging
from typing import Tuple, Type


def retry(exceptions: Tuple[Type[BaseException], ...], tries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry decorator with exponential backoff.

    Args:
        exceptions: Exceptions to catch and retry.
        tries: Maximum attempts (>=1).
        delay: Initial delay seconds between attempts.
        backoff: Multiplier after each failure.
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            _tries, _delay = tries, delay
            while _tries > 1:
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    logging.warning(f"{fn.__name__} failed: {e}. Retrying in {_delay:.1f}s…")
                    time.sleep(_delay)
                    _tries -= 1
                    _delay *= backoff
            # Last attempt, let exception propagate if it fails
            return fn(*args, **kwargs)
        return wrapper
    return deco
