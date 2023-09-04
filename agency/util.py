import inspect
import json
import os
import re
from datetime import datetime

from docstring_parser import DocstringStyle, parse


DEFAULT_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'


def to_timestamp(dt=datetime.now(), date_format=DEFAULT_TIMESTAMP_FORMAT):
    return dt.strftime(date_format)


def from_timestamp(timestamp_str, date_format=DEFAULT_TIMESTAMP_FORMAT):
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


def debug(key: str, object=None):
    """Pretty prints an object to the terminal for inspection"""
    if os.getenv("DEBUG", False):
        print(debug_text(key, object), flush=True)


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


def python_to_json_type_name(python_type_name: str) -> str:
    return {
        'str': 'string',
        'int': 'number',
        'float': 'number',
        'bool': 'boolean',
        'list': 'array',
        'dict': 'object'
    }[python_type_name]


def generate_help(method: callable) -> dict:
    """
    Generates a help object from a method's docstring and signature

    Args:
        method: the method

    Returns:
        A help object of the form:

        {
            "description": <description>,
            "args": {
                "arg_name": {
                    "type": <type>,
                    "description": <description>
                },
            }
            "returns": {
                "type": <type>,
                "description": <description>
            }
        }
    """
    signature = inspect.signature(method)
    parsed_docstring = parse(method.__doc__, DocstringStyle.GOOGLE)

    help_object = {}

    # description
    if parsed_docstring.short_description is not None:
        description = parsed_docstring.short_description
        if parsed_docstring.long_description is not None:
            description += " " + parsed_docstring.long_description
        help_object["description"] = re.sub(r"\s+", " ", description).strip()

    # args
    help_object["args"] = {}
    docstring_args = {arg.arg_name: arg for arg in parsed_docstring.params}
    arg_names = list(signature.parameters.keys())[1:]  # skip 'self' argument
    for arg_name in arg_names:
        arg_object = {}

        # type
        sig_annotation = signature.parameters[arg_name].annotation
        if sig_annotation is not None and sig_annotation.__name__ != "_empty":
            arg_object["type"] = python_to_json_type_name(
                signature.parameters[arg_name].annotation.__name__)
        elif arg_name in docstring_args and docstring_args[arg_name].type_name is not None:
            arg_object["type"] = python_to_json_type_name(
                docstring_args[arg_name].type_name)

        # description
        if arg_name in docstring_args and docstring_args[arg_name].description is not None:
            arg_object["description"] = docstring_args[arg_name].description.strip()

        help_object["args"][arg_name] = arg_object

    # returns
    if parsed_docstring.returns is not None:
        help_object["returns"] = {}

        # type
        if signature.return_annotation is not None:
            help_object["returns"]["type"] = python_to_json_type_name(
                signature.return_annotation.__name__)
        elif parsed_docstring.returns.type_name is not None:
            help_object["returns"]["type"] = python_to_json_type_name(
                parsed_docstring.returns.type_name)

        # description
        if parsed_docstring.returns.description is not None:
            help_object["returns"]["description"] = parsed_docstring.returns.description.strip()

    return help_object
