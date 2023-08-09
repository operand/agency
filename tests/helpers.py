import json
import time
from agency.agent import Agent, action


class Webster(Agent):
    """A fake agent for testing that ignores its own broadcasts by default"""
    def __init__(self, id: str, receive_own_broadcasts: bool = False):
        super().__init__(id, receive_own_broadcasts=receive_own_broadcasts)

    @action
    def say(self, content: str):
        """Use this action to say something to Webster"""

    @action
    def response(self, data, original_message_id: str):
        """Handles responses"""

    @action
    def error(self, error: str, original_message_id: str):
        """Handles errors"""


def wait_for_messages(agent, count=1, max_seconds=5):
    """
    A utility method to wait for messages to be processed. Throws an exception
    if the number of messages received goes over count, or if the timeout is
    reached.
    """
    print(f"{agent.id()} waiting {max_seconds} seconds for {count} messages...")
    start_time = time.time()
    while ((time.time() - start_time) < max_seconds):
        time.sleep(0.01)
        if len(agent._message_log) > count:
            raise Exception(
                f"too many messages received: {len(agent._message_log)} expected: {count}\n{json.dumps(agent._message_log, indent=2)}")
        if len(agent._message_log) == count:
            return
    raise Exception(
        f"too few messages received: {len(agent._message_log)} expected: {count}\n{json.dumps(agent._message_log, indent=2)}")