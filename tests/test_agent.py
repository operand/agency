from unittest.mock import MagicMock

import pytest

from agency.agent import Agent
from tests.helpers import Webster


def test_before_and_after_action():
    """
    Tests the before and after action callbacks
    """
    agent = Webster("Webster")
    agent.before_action = MagicMock()
    agent.after_action = MagicMock()
    agent._receive({
        "from": "Chatty",
        "to": "Webster",
        "action": {
            "name": "say",
            "args": {
                "content": "Hello, Webster!",
            },
        }
    })
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
    agent = Agent(valid_id)
    assert agent.id() == valid_id

    # Test id length
    too_short_id = ""
    too_long_id = "a" * 256
    with pytest.raises(ValueError):
        Agent(too_short_id)
    with pytest.raises(ValueError):
        Agent(too_long_id)

    # Test reserved sequence
    reserved_id = "amq.reserved"
    with pytest.raises(ValueError):
        Agent(reserved_id)

    # Test reserved broadcast id
    reserved_broadcast_id = "*"
    with pytest.raises(ValueError):
        Agent(reserved_broadcast_id)
