from colorama import Fore, Style
from everything.things.operator import ACCESS_REQUESTED, Operator, access_policy
import json
import os
import re
import subprocess


class Host(Operator):
    """
    Represents the host system of the running application
    """

    @access_policy(ACCESS_REQUESTED)
    def _action__shell_command(self, command: str):
        """Execute a shell command from the application root directory (/app) in
        a bash shell. Always use with caution."""
        command = ["bash", "-l", "-c", command]
        result = subprocess.run(
          command,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          text=True,
          cwd="/app" # TODO: make this configurable
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
