import json
import logging
import os
import traceback


_LOGLEVELS = {
    'CRITICAL': 50,
    'ERROR': 40,
    'WARNING': 30,
    'INFO': 20,
    'DEBUG': 10,
    'NOTSET': 0
}

_env_loglevel = os.environ.get('LOGLEVEL', 'WARNING').upper()
_LOGLEVEL = _LOGLEVELS[_env_loglevel]
_LOGFORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Initialize the logger
_logger = logging.getLogger("agency")
_logger.setLevel(_LOGLEVEL)
_handler = logging.StreamHandler()
_handler.setLevel(_LOGLEVEL)
_formatter = logging.Formatter(_LOGFORMAT)
_handler.setFormatter(_formatter)
_logger.addHandler(_handler)


class _CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


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
            if isinstance(object, Exception):
                # Print the traceback on exceptions
                pretty_object = "".join(traceback.format_exception(
                    etype=type(object), value=object, tb=object.__traceback__))
            else:
                # Try to json dumps it
                pretty_object = json.dumps(
                    object, indent=2, cls=_CustomEncoder)
        except:
            pass

    if pretty_object != None:
        message = f"{message}\n{pretty_object}"

    numeric_level = _LOGLEVELS.get(level.upper())
    if numeric_level is not None:
        _logger.log(numeric_level, message)
    else:
        raise ValueError(f"Invalid log level: {level}")
