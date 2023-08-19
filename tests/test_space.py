import time
from typing import List
from unittest.mock import MagicMock

import pytest

from agency.agent import Agent, RouterProtocol, action
from agency.schema import Message
from agency.space import Space
from agency.spaces.amqp_space import _AMQPRouter, AMQPOptions, AMQPSpace
from tests.helpers import ObservableAgent, add_agent, assert_message_log


class _Harford(ObservableAgent):
    @action
    def say(self, content: str):
        pass

class _TestableAMQPSpaceWithShortHeartbeat(AMQPSpace):
    def __init__(self):
        super().__init__(
            amqp_options=AMQPOptions(heartbeat=2),
            exchange_name="agency-test",
        )
        self.__test_router: RouterProtocol = _AMQPRouter(
            self._AMQPSpace__kombu_connection_options,
            self._AMQPSpace__exchange_name)

    def send_test_message(self, message: dict):
        """Send a message into the space for testing purposes"""
        self.__test_router.route(message)

def test_amqp_heartbeat():
    """
    Tests the amqp heartbeat is sent by setting a short heartbeat interval and
    ensuring the connection remains open.
    """
    amqp_space_with_short_heartbeat = _TestableAMQPSpaceWithShortHeartbeat()

    try:
        hartfords_message_log = add_agent(amqp_space_with_short_heartbeat, _Harford, "Hartford")

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
        amqp_space_with_short_heartbeat.send_test_message(message)
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
    Asserts that two agents may not have the same id in a MultiprocessSpace
    """
    multiprocess_space.add(Agent, "Webster")
    with pytest.raises(ValueError):
        multiprocess_space.add(Agent, "Webster")


@pytest.mark.focus
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


class _AfterAddAndBeforeRemoveAgent(ObservableAgent):
    """
    Writes to the _message_log after adding and before removing.
    """
    def __init__(self,
                 id: str,
                 router: RouterProtocol,
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
