import os
import time

import pytest

from agency.agent import Agent, action
from agency.space import Space
from agency.spaces.amqp_space import AMQPOptions, AMQPSpace
from agency.spaces.local_space import LocalSpace
from tests.conftest import SKIP_AMQP
from tests.helpers import assert_message_log


def test_add_and_remove_agent_local_space():
    space = LocalSpace()
    fg_agent = space.add_foreground(Agent, "ForegroundAgent")
    space.add(Agent, "BackgroundAgent")
    fg_agent.send({
        "to": "BackgroundAgent",
        "action": {"name": "help"}
    })
    assert_message_log(fg_agent._message_log, [
        {
            "from": "ForegroundAgent",
            "to": "BackgroundAgent",
            "action": {"name": "help"}
        },
        {
            "from": "BackgroundAgent",
            "to": "ForegroundAgent",
            "action": {
                "name": "[response]",
                "args": {
                    "value": {}
                }
            }
        }
    ])
    space.destroy()


class _Harford(Agent):
    @action
    def say(self, content: str):
        pass


@pytest.mark.skipif(SKIP_AMQP, reason=f"SKIP_AMQP={SKIP_AMQP}")
def test_amqp_heartbeat():
    """
    Tests the amqp heartbeat is sent by setting a short heartbeat interval and
    ensuring the connection remains open.
    """
    amqp_space_with_short_heartbeat = AMQPSpace(
        amqp_options=AMQPOptions(heartbeat=2), exchange_name="agency-test")

    try:
        hartford = amqp_space_with_short_heartbeat.add_foreground(
            _Harford, "Hartford")

        # wait enough time for connection to drop if no heartbeat is sent
        time.sleep(6)  # 3 x heartbeat

        # send yourself a message
        message = {
            "meta": {"id": "123"},
            "from": "Hartford",
            "to": "Hartford",
            "action": {
                "name": "say",
                "args": {
                    "content": "Hello",
                }
            },
        }
        hartford.send(message)
        assert_message_log(hartford._message_log, [
            message,  # send
            message,  # receive
        ])

    finally:
        # cleanup
        amqp_space_with_short_heartbeat.destroy()


def test_local_space_unique_ids(local_space):
    """
    Asserts that two agents may not have the same id in a LocalSpace
    """
    local_space.add(Agent, "Sender")
    with pytest.raises(ValueError):
        local_space.add(Agent, "Sender")


@pytest.mark.skipif(os.environ.get("SKIP_AMQP"), reason="Skipping AMQP tests")
def test_amqp_space_unique_ids():
    """
    Asserts that two agents may not have the same id in an AMQP space.
    """
    # For the amqp test, we create two AMQPSpace instances
    amqp_space1 = AMQPSpace(exchange_name="agency-test")
    amqp_space2 = AMQPSpace(exchange_name="agency-test")
    try:
        amqp_space1.add(Agent, "Sender")
        with pytest.raises(ValueError, match="Agent 'Sender' already exists"):
            amqp_space2.add(Agent, "Sender")
    finally:
        amqp_space1.destroy()
        amqp_space2.destroy()


class _AfterAddAndBeforeRemoveAgent(Agent):
    """
    Writes to the _message_log after adding and before removing.
    """

    def after_add(self):
        self._message_log.append("added")

    def before_remove(self):
        self._message_log.append("removed")


def test_after_add_and_before_remove(any_space: Space):
    """
    Tests that the after_add and before_remove methods are called.
    """
    # This first line calls space.add itself and returns the message log
    sender = any_space.add_foreground(_AfterAddAndBeforeRemoveAgent, "Sender")
    any_space.remove("Sender")

    assert list(sender._message_log) == ["added", "removed"]
