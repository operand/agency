import os
import subprocess

from agents.mixins.help_methods import HelpMethods

from agency.agent import ACCESS_REQUESTED, Agent, action


class Host(HelpMethods, Agent):
    """
    Represents the host system of the running application
    """

    @action(access_policy=ACCESS_REQUESTED)
    def shell_command(self, command: str) -> str:
        """Execute a shell command"""
        command = ["bash", "-l", "-c", command]
        result = subprocess.run(
          command,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          text=True,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            raise Exception(output)
        return output

    @action(access_policy=ACCESS_REQUESTED)
    def write_to_file(self, filepath: str, text: str, mode: str = "w") -> str:
        """Write to a file"""
        with open(filepath, mode) as f:
            f.write(text)
        return f"Wrote to {filepath}"

    @action(access_policy=ACCESS_REQUESTED)
    def read_file(self, filepath: str) -> str:
        """Read a file"""
        with open(filepath, "r") as f:
            text = f.read()
        return text

    @action(access_policy=ACCESS_REQUESTED)
    def delete_file(self, filepath: str) -> str:
        """Delete a file"""
        os.remove(filepath)
        return f"Deleted {filepath}"

    @action(access_policy=ACCESS_REQUESTED)
    def list_files(self, directory_path: str) -> str:
        """List files in a directory"""
        files = os.listdir(directory_path)
        return f"{files}"

    def request_permission(self, proposed_message: dict) -> bool:
        """Asks for permission on the command line"""
        # TODO: This functionality is temporarily disabled in the demo. All
        # actions are allowed for now.
        return True
