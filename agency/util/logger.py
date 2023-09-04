import json
import logging
import os


log_level = os.environ.get('LOGLEVEL', 'INFO').upper()


logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def debug_text(name, object=None):
    """Returns a pretty printed string for debugging"""
    START_STYLE = "\033[33m"  # yellow
    RESET_STYLE = "\033[0m"
    debug_value = ""
    if object != None:
        debug_object_value = object
        try:
            # since this is always for a human we hardcode 2 space indentation
            debug_object_value = json.dumps(
                object, indent=2, cls=CustomEncoder)
        except Exception as e:
            print(f"debug_text: {e}")
            pass
        debug_value = f"{debug_object_value}\n{RESET_STYLE}{'_'*5} {name} {'_'*5}"
    return f"\n{START_STYLE}{'>'*5} {name} {'<'*5}{RESET_STYLE}\n{debug_value}{RESET_STYLE}".replace("\\n", "\n")


def log(level: str, message: str):
    """Logs a message at the specified level"""
    message = debug_text(level, message)
    logger.log(level.upper(), message)
