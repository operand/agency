import os
import subprocess
from channels.channel import Channel




# TODO
# def _pre_prompt(self, actor, timestamp=util.get_current_timestamp()):
#   actor_name = type(actor).__name__
#   return f"{ANSI_STYLES[actor_name]}[{timestamp}] {actor_name}:{Style.RESET_ALL} "


# print(
#   f"{Back.RED + Fore.BLACK}---Permission Requested---{Style.RESET_ALL}\naction: {json.dumps(message['action'])}\n--------------------------")
# permission_response = input(
#   f"Permission requested to execute \"{message['action']}\"? (y/n)")
# return re.search(r"^y(es)?$", permission_response)


class OSChannel(Channel):
  """
  Channel to the operating system of the running application
  """

  def action__shell_command(self, command: str):
    """
    Execute a shell command within the System's linux environment (based on
    python:latest). Always use with caution. Commands are executed from the
    application root directory (/app) within a bash shell."""
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
  action__shell_command.access = "ask"

  def action__write_to_file(self, filepath: str, text: str, mode: str = "w"):
    """Write to a file"""
    with open(filepath, mode) as f:
      f.write(text)
    return f"Wrote to {filepath}"
  action__write_to_file.access = "ask"

  def action__read_file(self, filepath: str):
    """Read a file"""
    with open(filepath, "r") as f:
      text = f.read()
    return text
  action__read_file.access = "ask"

  def action__delete_file(self, filepath: str):
    """Delete a file"""
    os.remove(filepath)
    return f"Deleted {filepath}"
  action__delete_file.access = "ask"

  def action__list_files(self, directory_path: str):
    """List files in a directory"""
    files = os.listdir(directory_path)
    return f"{files}"
  action__list_files.access = "ask"