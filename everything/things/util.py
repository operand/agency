import datetime
from ctypes import ArgumentError
from datetime import datetime
import inspect
import re
from typing import get_type_hints
import regex
import json
from colorama import Fore, Style


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


# returns the first substring surrounded by {} that doesn't contain a stop
# string
# TODO: make this an lm function?
def extract_json_string(input_string, stopping_strings):
  pattern = r"\{(?:[^{}]*|(?R))*\}"
  matches = regex.findall(pattern, input_string, re.DOTALL)
  valid_matches = [
    match for match in matches if not any(
      stop_string in match for stop_string in stopping_strings
    )
  ]
  if len(valid_matches) == 0:
    raise ArgumentError(f"Couldn't find valid JSON in {input_string}")
  return valid_matches[0]


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
  START_STYLE = Style.RESET_ALL + Fore.YELLOW
  END_STYLE = Style.RESET_ALL
  debug_name = f"{name}"
  debug_value = ""
  if object != None:
    debug_name = f"{type(object)}:{name}"
    debug_object_value = object
    try:
      # since this is always for a human we hardcode 2 space indentation
      debug_object_value = json.dumps(object, indent=2, cls=CustomEncoder)
    except Exception as e:
      print(f"debug_text: {e}")
      pass
    debug_value = f"{debug_object_value}\n{END_STYLE}{'_'*5} {debug_name} {'_'*5}"

  return f"\n{START_STYLE}{'>'*5} {debug_name} {'<'*5}{Style.RESET_ALL}\n{debug_value}{Style.RESET_ALL}".replace("\\n", "\n")


def parse_json_response(response_text, stopping_string) -> dict:
  """
  Parses a json command string into a valid action object
  """
  try:
    message_json = json.loads(
      # try to parse everything up to the first stopping string found
      response_text.split(stopping_string)[0].strip()
    )
    return message_json
  except Exception as e:
    raise f"{e}: Could not parse command from: \"{response_text}\""


def parse_slash_syntax_action(action_text) -> dict:
  """
  Parses commands of the following syntax:

  /actionname arg1:val1 arg2:val2 arg3:

  into an object like this:

  {
    "action": "actionname",
    "args": {
      "arg1": "val1",
      "arg2": "val2",
      "arg3": True
    }
  }

  With the following rules:

  - A command starts with a slash and must be the first word.
  - If a slash does not begin the string, assume the /say command, and the
    entire string is the "content" arg.
  - The command name is always the first word after the slash.
  - The arguments are key:value pairs, separated by spaces.
  - The value can be a string, a number, a boolean, or a json object.
  - The value can be quoted with single or double quotes.
  - A string value must be quoted if it contains spaces.
  - The value can be omitted, in which case it is assumed to be "True" as in the
    arg3 example above.

  This method does NOT validate the action object, it only parses it.
  """
  # Handle /say command case
  if not action_text.startswith("/"):
    return {
      "action": "say",
      "args": {"content": action_text}
    }

  parts = action_text.split()
  command = parts[0][1:]
  args = {}

  for part in parts[1:]:
    key, *val = part.split(":", 1)
    val = val[0] if val else True
    try:
      args[key] = json.loads(val.strip('\'"'))
    except json.JSONDecodeError:
      args[key] = val

  action = {
    "action": command,
    "args": args,
  }
  return action
