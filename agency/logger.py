import json
import logging
import os
import traceback

import colorlog
from colorlog import escape_codes
from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import get_lexer_by_name

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
_LOGFORMAT = '%(asctime_color)s%(asctime)s%(reset_color)s - %(levelname_color)s%(levelname)s%(reset_color)s - %(message_color)s%(message)s%(reset_color)s%(object_color)s%(object)s%(reset_color)s'
_LOG_PYGMENTS_STYLE = os.environ.get('LOG_PYGMENTS_STYLE', 'monokai')


class CustomColoredFormatter(colorlog.ColoredFormatter):
    def format(self, record):
        record.reset_color = escape_codes.escape_codes['reset']
        record.asctime_color = escape_codes.escape_codes['light_black']
        record.levelname_color = escape_codes.escape_codes[self.log_colors[record.levelname]]
        record.message_color = escape_codes.escape_codes['reset']
        record.object_color = escape_codes.escape_codes['reset']

        return super().format(record)


_logger = logging.getLogger("agency")
_logger.setLevel(_LOGLEVEL)
_handler = logging.StreamHandler()
_handler.setLevel(_LOGLEVEL)

_formatter = CustomColoredFormatter(
    _LOGFORMAT,
    log_colors={
        'CRITICAL': 'bold_red',
        'ERROR': 'red',
        'WARNING': 'yellow',
        'INFO': 'green',
        'DEBUG': 'cyan',
    }
)

_handler.setFormatter(_formatter)
_logger.addHandler(_handler)


class _CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def log(level: str, message: str, object=None):
    pretty_object: str = ""
    if object != None:
        try:
            if isinstance(object, Exception):
                pretty_object = "\n" + "".join(traceback.format_exception(
                    etype=type(object), value=object, tb=object.__traceback__))
            else:
                json_str = json.dumps(object, indent=2, cls=_CustomEncoder)
                pretty_object = "\n" + \
                    highlight(json_str, get_lexer_by_name('json'),
                              Terminal256Formatter(style=_LOG_PYGMENTS_STYLE))
        except:
            pass

    numeric_level = _LOGLEVELS.get(level.upper())
    if numeric_level is not None:
        _logger.log(numeric_level, message, extra={'object': pretty_object})
    else:
        raise ValueError(f"Invalid log level: {level}")
