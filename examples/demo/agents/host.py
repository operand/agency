import json
import os
import subprocess
import uuid
from typing import Dict

from agents.mixins.help_methods import HelpMethods
from colorama import Fore, Style

from agency.agent import ACCESS_REQUESTED, Agent, QueueProtocol, action


class Host(HelpMethods, Agent):
    """
    Represents the host system of the running application
    """

    def __init__(self, id: str,
                 outbound_queue: QueueProtocol = None,
                 receive_own_broadcasts: bool = True,
                 admin_id: str = None):
        super().__init__(id, outbound_queue, receive_own_broadcasts=False)
        # the id of the admin to ask for permission
        self.admin_id = admin_id
        # used by the request_permission method to asynchronously ask for permission
        self.pending_permissions: Dict[str, bool] = {}

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

        if proposed_message["from"] == self.admin_id:
            return True

        else:
            # send a message to the admin for permission
            text = \
                f"{Fore.RED}***** Permission requested to execute: *****{Style.RESET_ALL}\n" + \
                json.dumps(proposed_message, indent=2) + \
                f"\n{Fore.RED}^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^{Style.RESET_ALL}\n" + \
                "Allow? (y/n) "

            response = self.send_and_await_reply({
                "id": f"request_permission-{uuid.uuid4()}",
                "to": self.admin_id,
                "action": {
                    "name": "say",
                    "content": text,
                }
            })

            # return re.search(r"^y(es)?$", response)

    def response(self, data, original_message_id: str):
        if original_message_id == "request_permission":
            # handle a permission response and execute the command
            pass
