import json
import multiprocessing
import time
from typing import List

from agency.agent import Agent, RouterProtocol
from agency.schema import Message
from agency.space import Space

# The following class and helper methods can be used together to provide
# observability across processes and threads for testing purposes.


class ObservableAgent(Agent):
    """
    Agent class that receives a custom _message_log for inspecting in tests.

    This class also ignores its own broadcasts by default for convenience.
    """

    def __init__(self,
                 id: str,
                 router: RouterProtocol,
                 receive_own_broadcasts: bool = False,
                 _message_log: List[Message] = []):
        super().__init__(id, router, receive_own_broadcasts)
        self._message_log = _message_log


def add_agent(space: Space, agent_type: ObservableAgent, agent_id: str, **agent_kwargs) -> List[Message]:
    """
    Adds an agent to a space and return a reference to its _message_log for
    testing.
    """
    _message_log = multiprocessing.Manager().list()  # thread and process safe
    space.add(agent_type, agent_id, **agent_kwargs, _message_log=_message_log)
    return _message_log


def assert_message_log(actual: List[Message], expected: List[Message], max_seconds=10):
    """
    Asserts that a list of messages is as expected.
    """
    print(f"waiting {max_seconds} seconds for {len(expected)} messages...")
    start_time = time.time()
    while ((time.time() - start_time) < max_seconds):
        time.sleep(0.01)
        actual = list(actual)  # cast to list
        if len(actual) > len(expected):
            raise Exception(
                f"too many messages received: {len(actual)} expected: {len(expected)}\n{json.dumps(actual, indent=2)}")
        if len(actual) == len(expected):
            assert actual == expected
            return
    raise Exception(
        f"too few messages received: {len(actual)} expected: {len(expected)}\n{json.dumps(actual, indent=2)}")
