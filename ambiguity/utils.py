"""Some miscellaneous utilities"""
import signal


class Timeout:  # pylint: disable=too-few-public-methods
    """Context manager to raise a TimeoutError exception if it isn't exited
    after some amount of time"""

    def __init__(self, seconds=10, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, *_args):
        """Callback when the time has elapsed"""
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, *_args):
        signal.alarm(0)


class Namespace:  # pylint: disable=too-few-public-methods
    """Simple class that takes a dictionary and makes a namespace"""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        lines = ["Namespace with {} items".format(len(self.__dict__))]
        for name, value in self.__dict__.items():
            lines.append("    {}: {}".format(name, value))
        return "\n".join(lines)
