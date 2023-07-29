from datetime import datetime
from typing import get_type_hints
import inspect
import json
import re


SYSTEM_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'
NATURAL_TIMESTAMP_FORMAT = '%A %B %d, %Y, %H:%M%p'


def to_timestamp(dt=datetime.now(), date_format=SYSTEM_TIMESTAMP_FORMAT):
    return dt.strftime(date_format)


def from_timestamp(timestamp_str, date_format=SYSTEM_TIMESTAMP_FORMAT):
    return datetime.datetime.strptime(timestamp_str, date_format)


def extract_json(input: str, stopping_strings: list = []):
    stopping_string = next((s for s in stopping_strings if s in input), '')
    split_string = input.split(stopping_string, 1)[
        0] if stopping_string else input
    start_position = split_string.find('{')
    end_position = split_string.rfind('}') + 1

    if start_position == -1 or end_position == -1 or start_position > end_position:
        raise ValueError(f"Couldn't find valid JSON in \"{input}\"")

    try:
        return json.loads(split_string[start_position:end_position])
    except json.JSONDecodeError:
        raise ValueError(f"Couldn't parse JSON in \"{input}\"")


def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)


def print_warning(text):
    print(f"\033[93mWARNING: {text}\033[0m")


# enables debug messages for the listed keys
DEBUG_KEYS = {
  "*", # special key, uncomment to force enable all debug messages
  # "-", # special key, uncomment to force disable all debug messages

  # you can also list keys to watch directly below:
  # "abc",
  # ...
}


def debug(name, object=None):
    """pretty prints an object to the terminal for inspection"""
    if (
        name
        and (
            name in DEBUG_KEYS and
            "-" not in DEBUG_KEYS  # - overrides others and globally disables
            and not name.startswith("*")  # starting with * overrides -
        ) or (
            name not in DEBUG_KEYS
            and name.startswith("*")  # * forces debug message
            or (
                "*" in DEBUG_KEYS
                and "-" not in DEBUG_KEYS  # - overrides * here
                # -{name} disables specific messages when * is on
                    and f"-{name}" not in DEBUG_KEYS
            )
        )
    ):
        print(debug_text(name, object), flush=True)


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def debug_text(name, object=None):
    """
    Returns a pretty printed string for debugging
    """
    START_STYLE = "\033[33m" # yellow
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


def python_to_json_type_name(python_type_name: str) -> str:
    return {
        'str': 'string',
        'int': 'number',
        'float': 'number',
        'bool': 'boolean',
        'list': 'array',
        'dict': 'object'
    }[python_type_name]
