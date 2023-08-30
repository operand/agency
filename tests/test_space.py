import time
from typing import List

import pytest

from agency.agent import Agent, QueueProtocol, action
from agency.schema import Message
from agency.space import Space
from agency.spaces.amqp_space import AMQPOptions, AMQPSpace
from tests.helpers import ObservableAgent, add_agent, assert_message_log


class _Harford(ObservableAgent):
    @action
    def say(self, content: str):
        pass


def test_amqp_heartbeat():
    """
    Tests the amqp heartbeat is sent by setting a short heartbeat interval and
    ensuring the connection remains open.
    """
    amqp_space_with_short_heartbeat = AMQPSpace(
        amqp_options=AMQPOptions(heartbeat=2), exchange_name="agency-test")

    try:
        hartfords_message_log = add_agent(
            amqp_space_with_short_heartbeat, _Harford, "Hartford")

        # wait enough time for connection to drop if no heartbeat is sent
        time.sleep(6)  # 3 x heartbeat

        # send yourself a message
        message = {
            "from": "Hartford",
            "to": "Hartford",
            "action": {
                "name": "say",
                "args": {
                    "content": "Hello",
                }
            },
        }
        amqp_space_with_short_heartbeat._route(message)
        assert_message_log(hartfords_message_log, [message])

    finally:
        # cleanup
        amqp_space_with_short_heartbeat.remove_all()


def test_thread_space_unique_ids(thread_space):
    """
    Asserts that two agents may not have the same id in a ThreadSpace
    """
    thread_space.add(Agent, "Webster")
    with pytest.raises(ValueError):
        thread_space.add(Agent, "Webster")


def test_multiprocess_space_unique_ids(multiprocess_space):
    """
    Asserts that two agents may not have the same id in a ThreadSpace
    """
    multiprocess_space.add(Agent, "Webster")
    with pytest.raises(ValueError):
        multiprocess_space.add(Agent, "Webster")


def test_amqp_space_unique_ids():
    """
    Asserts that two agents may not have the same id in an AMQP space.
    """
    # For the amqp test, we create two AMQPSpace instances
    amqp_space1 = AMQPSpace(exchange_name="agency-test")
    amqp_space2 = AMQPSpace(exchange_name="agency-test")
    try:
        amqp_space1.add(Agent, "Webster")
        with pytest.raises(ValueError):
            amqp_space2.add(Agent, "Webster")
    finally:
        amqp_space1.remove_all()
        amqp_space2.remove_all()


def test_invalid_message(any_space):
    """
    Asserts that an invalid message raises a ValueError

    This isn't the greatest test since it relies on the internal Router of each
    space but it's okay for now.
    """
    with pytest.raises(ValueError):
        any_space.send_test_message("blah")

    with pytest.raises(ValueError):
        any_space.send_test_message({})


class _AfterAddAndBeforeRemoveAgent(ObservableAgent):
    """
    Writes to the _message_log after adding and before removing.
    """

    def __init__(self,
                 id: str,
                 router: QueueProtocol,
                 receive_own_broadcasts: bool = False,
                 _message_log: List[Message] = None):
        super().__init__(id,
                         router,
                         receive_own_broadcasts,
                         _message_log)

    def after_add(self):
        self._message_log.append("added")

    def before_remove(self):
        self._message_log.append("removed")


def test_after_add_and_before_remove(any_space: Space):
    """
    Tests that the after_add and before_remove methods are called.
    """
    # This first line calls space.add itself and returns the message log
    log = add_agent(any_space, _AfterAddAndBeforeRemoveAgent, "Webster")
    any_space.remove("Webster")

    assert list(log) == ["added", "removed"]
