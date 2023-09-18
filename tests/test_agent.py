import threading
from unittest.mock import MagicMock

import pytest

from agency.agent import Agent, action
from tests.helpers import ObservableAgent


class BeforeAndAfterActionAgent(ObservableAgent):
    @action
    def say(self, content: str):
        pass


def test_before_and_after_action():
    """
    Tests the before and after action callbacks
    """
    agent = BeforeAndAfterActionAgent("Agent", outbound_queue=MagicMock())
    agent.before_action = MagicMock()
    agent.after_action = MagicMock()

    # Create an event to signal when the thread has completed its execution
    thread_complete = threading.Event()

    def on_thread_complete():
        thread_complete.set()
    # Modify the after_action callback to call on_thread_complete when it's done
    original_after_action = agent.after_action
    agent.after_action = MagicMock(
        side_effect=lambda *args, **kwargs: (
            original_after_action(*args, **kwargs),
            on_thread_complete()
        )[0]
    )

    agent._receive({
        "meta": {"id": "123"},
        "from": "Agent",
        "to": "Agent",
        "action": {
            "name": "say",
            "args": {
                "content": "Hello, Agent!",
            },
        }
    })

    # Wait for the thread to complete
    thread_complete.wait(timeout=2)

    agent.before_action.assert_called_once()
    agent.after_action.assert_called_once()


def test_id_validation():
    """
    Asserts ids are:
    - 1 to 255 characters in length
    - Cannot start with the reserved sequence `"amq."`
    - Cannot use the reserved broadcast id "*"
    """
    # Test valid id
    valid_id = "valid_agent_id"
    agent = Agent(valid_id, outbound_queue=MagicMock())
    assert agent.id() == valid_id

    # Test id length
    too_short_id = ""
    too_long_id = "a" * 256
    with pytest.raises(ValueError):
        Agent(too_short_id, outbound_queue=MagicMock())
    with pytest.raises(ValueError):
        Agent(too_short_id, outbound_queue=MagicMock())

    # Test reserved sequence
    reserved_id = "amq.reserved"
    with pytest.raises(ValueError):
        Agent(too_short_id, outbound_queue=MagicMock())

    # Test reserved broadcast id
    reserved_broadcast_id = "*"
    with pytest.raises(ValueError):
        Agent(reserved_broadcast_id, outbound_queue=MagicMock())
