from colorama import Fore, Style
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


def get_arg_names_and_types(method):
    """
    Returns a dictionary of argument names and types for a given method
    """
    args = inspect.signature(method).parameters
    args_dict = {}
    for arg_name, _arg in args.items():
        if arg_name == 'self':
            continue  # Skip 'self' argument
        arg_type = get_type_hints(method).get(arg_name, None)
        args_dict[arg_name] = str(arg_type) if arg_type else None
    return args_dict


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

# Example usage:
# colored_string = "\033[31mHello, \033[32mWorld!\033[0m"
# print(strip_ansi_codes(colored_string))


def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)


def breakpoint():
    import pdb
    pdb.set_trace()


# enables debug messages for the listed keys
DEBUG_KEYS = {
  # "*", # special key, uncomment to force enable all debug messages
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
    START_STYLE = Style.RESET_ALL + Fore.YELLOW
    END_STYLE = Style.RESET_ALL
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
        debug_value = f"{debug_object_value}\n{END_STYLE}{'_'*5} {name} {'_'*5}"
    return f"\n{START_STYLE}{'>'*5} {name} {'<'*5}{Style.RESET_ALL}\n{debug_value}{Style.RESET_ALL}".replace("\\n", "\n")
