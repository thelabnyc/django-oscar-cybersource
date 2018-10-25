from functools import wraps
import time
import traceback


def retry(ExceptionToCheck, tries=4, delay=2, backoff=2):
    def decorator(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return fn(*args, **kwargs)
                except ExceptionToCheck:
                    print("\n")
                    traceback.print_exc()
                    print("Retrying in {} seconds...".format(mdelay))
                    print("\n")
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return fn(*args, **kwargs)
        return inner
    return decorator
