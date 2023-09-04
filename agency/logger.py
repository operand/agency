import json
import logging
import os


class _CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()


logging.basicConfig(
    level=LOGLEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

_logger = logging.getLogger(__name__)

_LOG_LEVELS = {
    'CRITICAL': 50,
    'ERROR': 40,
    'WARNING': 30,
    'INFO': 20,
    'DEBUG': 10,
    'NOTSET': 0
}


def log(level: str, message: str, object: object = None):
    """
    Logs a message at the specified level

    If the object argument is provided, it will be pretty printed after the
    message.

    Args:
        level: The log level
        message: The message
        object: An optional object to pretty print
    """
    pretty_object: str = None
    if object != None:
        try:
            # Try to json dumps it
            pretty_object = json.dumps(object, indent=2, cls=_CustomEncoder)
        except:
            pass

    if pretty_object != None:
        message = f"{message}\n{pretty_object}"

    numeric_level = _LOG_LEVELS.get(level.upper())
    if numeric_level is not None:
        _logger.log(numeric_level, message)
    else:
        raise ValueError(f"Invalid log level: {level}")
