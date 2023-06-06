import json
import os
import re
import subprocess
import textwrap
from colorama import Fore, Style
from everything.things.channel import ACCESS_REQUESTED, Channel, access_policy


# TODO
# def _pre_prompt(self, actor, timestamp=util.get_current_timestamp()):
#   actor_name = type(actor).__name__
#   return f"{ANSI_STYLES[actor_name]}[{timestamp}] {actor_name}:{Style.RESET_ALL} "

# print(
#   f"{Back.RED + Fore.BLACK}---Permission Requested---{Style.RESET_ALL}\naction: {json.dumps(message['action'])}\n--------------------------")
# permission_response = input(
#   f"Permission requested to execute \"{message['action']}\"? (y/n)")
# return re.search(r"^y(es)?$", permission_response)


class HostChannel(Channel):
  """
  Channel to the host system of the running application
  """

  @access_policy(ACCESS_REQUESTED)
  def _action__shell_command(self, command: str):
    """Execute a shell command within the System's environment. Always use with
    caution. Commands are executed from the application root directory (/app)
    within a bash shell."""
    script_directory = os.path.dirname(os.path.abspath(__file__) + "/../")
    command = f"bash -l -c '{command}'"
    result = subprocess.run(
      command,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE, text=True, cwd=script_directory
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
      raise Exception(output)
    return output

  @access_policy(ACCESS_REQUESTED)
  def _action__write_to_file(self, filepath: str, text: str, mode: str = "w"):
    """Write to a file"""
    with open(filepath, mode) as f:
      f.write(text)
    return f"Wrote to {filepath}"

  @access_policy(ACCESS_REQUESTED)
  def _action__read_file(self, filepath: str):
    """Read a file"""
    with open(filepath, "r") as f:
      text = f.read()
    return text

  @access_policy(ACCESS_REQUESTED)
  def _action__delete_file(self, filepath: str):
    """Delete a file"""
    os.remove(filepath)
    return f"Deleted {filepath}"

  @access_policy(ACCESS_REQUESTED)
  def _action__list_files(self, directory_path: str):
    """List files in a directory"""
    files = os.listdir(directory_path)
    return f"{files}"

  def _request_permission(self, proposed_message: dict) -> bool:
    """Asks for permission on the command line"""
    text = \
    f"{Fore.RED}***** Permission requested to execute: *****{Style.RESET_ALL}\n" + \
    json.dumps(proposed_message, indent=2) + \
    f"\n{Fore.RED}^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^{Style.RESET_ALL}\n"
    print(text)
    permission_response = input("Allow? (y/n) ")
    return re.search(r"^y(es)?$", permission_response)
  