import functools
import logging


def log_exceptions(f, re_raise=True):
    """Decorator to log exceptions that are easy to lose in Tornado callbacks"""

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logging.getLogger().exception(e)
            if re_raise:
                raise e
    return wrapped
