import time
from unittest.mock import MagicMock

import pytest

from agency.agent import Agent, action
from agency.spaces.amqp_space import AMQPOptions, AMQPSpace
from tests.helpers import Webster, wait_for_messages


def test_heartbeat():
    """
    Tests the amqp heartbeat is sent by setting a short heartbeat interval and
    ensuring the connection remains open.
    """
    amqp_space_with_short_heartbeat = AMQPSpace(
        amqp_options=AMQPOptions(heartbeat=2),
        exchange="agency-test",
    )

    class Harford(Agent):
        @action
        def say(self, content: str):
            pass

    hartford = Harford("Hartford")
    amqp_space_with_short_heartbeat.add(hartford)

    # wait enough time for connection to drop if no heartbeat is sent
    time.sleep(6)  # 3 x heartbeat

    # send yourself a message
    message = {
        "from": hartford.id(),
        "to": hartford.id(),
        "action": {
            "name": "say",
            "args": {
                "content": "Hello",
            }
        },
    }
    hartford.send(message)
    wait_for_messages(hartford, count=2, max_seconds=5)

    # should receive the outgoing and incoming messages
    assert len(hartford._message_log) == 2
    assert hartford._message_log == [message, message]

    # cleanup
    amqp_space_with_short_heartbeat.remove(hartford)


def test_unique_ids_native(native_space):
    """
    Asserts that two agents may NOT have the same id
    """
    native_space.add(Webster("Webster"))
    with pytest.raises(ValueError):
        native_space.add(Webster("Webster"))


def test_unique_ids_amqp(amqp_space):
    """
    Asserts that two agents may NOT have the same id
    """
    # For the amqp test, we create another AMQPSpace instance to add the second
    # agent.
    amqp_space2 = AMQPSpace(exchange="agency-test")

    amqp_space.add(Webster("Webster"))
    with pytest.raises(ValueError):
        amqp_space2.add(Webster("Webster"))


def test_after_add_and_before_remove(either_space):
    """
    Tests that the _after_add and _before_remove methods are called when an
    agent is added to and removed from a space.
    """
    agent = Webster("Webster")
    agent.after_add = MagicMock()
    either_space.add(agent)
    agent.after_add.assert_called_once()

    agent.before_remove = MagicMock()
    either_space.remove(agent)
    agent.before_remove.assert_called_once()