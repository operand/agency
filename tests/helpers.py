import json
import multiprocessing
import time
from typing import List

from agency.agent import Agent, _QueueProtocol
from agency.schema import Message
from agency.space import Space

multiprocessing.set_start_method('spawn', force=True)


# The following class and helper methods can be used together to provide
# observability across processes and threads for testing purposes.


class ObservableAgent(Agent):
    """
    Agent class that accepts a custom _message_log for inspection in tests.

    This class also ignores its own broadcasts by default for convenience.
    """

    def __init__(self,
                 id: str,
                 outbound_queue: _QueueProtocol,
                 receive_own_broadcasts: bool = False,
                 _message_log: List[Message] = []):
        super().__init__(id, outbound_queue=outbound_queue,
                         receive_own_broadcasts=receive_own_broadcasts)
        self._message_log = _message_log


def add_agent(space: Space, agent_type: ObservableAgent, agent_id: str, **agent_kwargs) -> List[Message]:
    """
    Adds an agent to a space and returns a reference to its _message_log for
    testing.
    """
    _message_log = multiprocessing.Manager().list()  # thread and process safe
    space.add(agent_type, agent_id, **agent_kwargs, _message_log=_message_log)
    return _message_log


def assert_message_log(actual: List[Message], expected: List[Message], max_seconds=2):
    """
    Asserts that a list of messages is as expected.
    """
    wait_for_length(actual, len(expected), max_seconds)
    print(f"list type: {type(list(actual))}")
    assert list(actual) == list(expected), \
        f"\nActual: {json.dumps(list(actual), indent=2)}\nExpected: {json.dumps(expected, indent=2)}"


def wait_for_length(actual_list: List, expected_length: int, max_seconds=2):
    """Waits for the agent's _message_log to be populated."""
    print(f"Waiting {max_seconds} seconds for {expected_length} messages...")
    start_time = time.time()
    while ((time.time() - start_time) < max_seconds):
        time.sleep(0.01)
        actual = list(actual_list)  # cast to list
        if len(actual) > expected_length:
            raise Exception(
                f"too many messages received: {len(actual)} expected: {expected_length}\n{json.dumps(actual, indent=2)}")
        if len(actual) == expected_length:
            return
    raise Exception(
        f"too few messages received: {len(actual)} expected: {expected_length}\n{json.dumps(actual, indent=2)}")
