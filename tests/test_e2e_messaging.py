import time

import pytest

from agency.agent import ActionError, Agent, action
from agency.space import Space
from tests.helpers import assert_message_log


class _MessagingTestAgent(Agent):
    @action
    def null_action(self, *args, **kwargs):
        """
        This action does nothing. It accepts any arguments for convenience.
        """

    @action
    def slow_action(self):
        """This action sleeps for 3 seconds"""
        time.sleep(3)

    @action
    def action_with_reply(self):
        """Replies to the message sender using send()"""
        self.send({
            "to": self.current_message()['from'],
            "action": {
                "name": "null_action",
                "args": {
                    "content": f"Hello, {self.current_message()['from']}!",
                }
            }
        })

    @action
    def action_with_response(self):
        self.respond_with(["Hello!"])

    @action
    def action_with_error(self):
        raise ValueError("Something went wrong")


def test_send_and_reply(any_space: Space):
    """Tests sending/receiving a basic send()"""
    sender = any_space.add_foreground(_MessagingTestAgent, "Sender")
    any_space.add(_MessagingTestAgent, "Receiver")

    # Send the first message and wait for a response
    first_message = {
        "meta": {
            "id": "123"
        },
        "from": "Sender",
        "to": "Receiver",
        "action": {
            "name": "action_with_reply",
        }
    }
    sender.send(first_message)
    assert_message_log(sender._message_log, [
        first_message,
        {
            "meta": {},
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "null_action",
                "args": {
                    "content": "Hello, Sender!",
                }
            },
        },
    ])


def test_send_and_error(any_space: Space):
    sender = any_space.add_foreground(Agent, "Sender")
    any_space.add(_MessagingTestAgent, "Receiver")

    # this message will result in an error
    first_message = {
        "meta": {
            "id": "123",
        },
        "to": "Receiver",
        "from": "Sender",
        "action": {
            "name": "action_with_error",
        }
    }
    sender.send(first_message)
    assert_message_log(sender._message_log, [
        first_message,
        {
            "meta": {"parent_id": "123"},
            "to": "Sender",
            "from": "Receiver",
            "action": {
                "name": "[error]",
                "args": {
                    "error": "ValueError: Something went wrong",
                }
            }
        }])


def test_send_and_respond(any_space: Space):
    sender = any_space.add_foreground(Agent, "Sender")
    any_space.add(_MessagingTestAgent, "Receiver")

    first_message = {
        "meta": {
            "id": "123 whatever i feel like here"
        },
        "to": "Receiver",
        "from": "Sender",
        "action": {
            "name": "action_with_response",
        }
    }
    sender.send(first_message)
    assert_message_log(sender._message_log, [
        first_message,
        {
            "meta": {
                "parent_id": "123 whatever i feel like here",
            },
            "to": "Sender",
            "from": "Receiver",
            "action": {
                "name": "[response]",
                "args": {
                    "value": ["Hello!"],
                }
            }
        }
    ])


def test_request_and_respond(any_space: Space):
    sender = any_space.add_foreground(Agent, "Sender")
    any_space.add(_MessagingTestAgent, "Receiver")

    assert sender.request({
        "to": "Receiver",
        "action": {
            "name": "action_with_response",
        }
    }) == ["Hello!"]


def test_request_and_error(any_space: Space):
    sender = any_space.add_foreground(Agent, "Sender")
    any_space.add(_MessagingTestAgent, "Receiver")

    with pytest.raises(ActionError, match="ValueError: Something went wrong"):
        sender.request({
            "to": "Receiver",
            "action": {
                "name": "action_with_error",
            }
        })


def test_request_and_timeout(any_space: Space):
    sender = any_space.add_foreground(Agent, "Sender")
    any_space.add(_MessagingTestAgent, "Receiver")

    with pytest.raises(TimeoutError):
        sender.request({
            "to": "Receiver",
            "action": {
                "name": "slow_action",
            }
        }, timeout=0.1)


def test_self_received_broadcast(any_space: Space):
    sender = any_space.add_foreground(
        Agent, "Sender", receive_own_broadcasts=True)
    receiver = any_space.add_foreground(Agent, "Receiver")
    first_message = {
        "meta": {
            "id": "123",
        },
        "from": "Sender",
        "to": "*",  # makes it a broadcast
        "action": {
            "name": "null_action",
            "args": {
                "content": "Hello, everyone!",
            },
        },
    }
    sender.send(first_message)
    assert_message_log(sender._message_log, [
        first_message,  # send broadcast
        first_message,  # receipt of bcast
    ])
    assert_message_log(receiver._message_log, [
        first_message,  # receipt of bcast
    ])


def test_non_self_received_broadcast(any_space: Space):
    sender = any_space.add_foreground(
        Agent, "Sender", receive_own_broadcasts=False)
    receiver = any_space.add_foreground(Agent, "Receiver")

    first_message = {
        "meta": {
            "id": "123",
        },
        "from": "Sender",
        "to": "*",  # makes it a broadcast
        "action": {
            "name": "null_action",
            "args": {
                "content": "Hello, everyone!",
            },
        },
    }
    sender.send(first_message)
    assert_message_log(sender._message_log, [
        first_message,  # send broadcast
        # --- NO receipt of bcast here ---
    ])
    assert_message_log(receiver._message_log, [
        first_message,  # receipt of bcast
    ])


def test_meta(any_space: Space):
    """Tests the meta field"""

    sender = any_space.add_foreground(Agent, "Sender")
    receiver = any_space.add_foreground(_MessagingTestAgent, "Receiver")

    first_message = {
        "meta": {
            "id": "123",  # id is required
            "something": "made up",  # everything else is optional
            "foo": 0,
            "bar": ["baz"]
        },
        "from": "Sender",
        "to": "Receiver",
        "action": {
            "name": "null_action",
        },
    }
    sender.send(first_message)
    assert_message_log(receiver._message_log, [
        first_message,  # asserts receiving the meta unchanged
    ], ignore_unexpected_meta_keys=False)


def test_send_undefined_action(any_space: Space):
    """Tests sending an undefined action and receiving an error response"""

    sender = any_space.add_foreground(Agent, "Sender")
    any_space.add(Agent, "Receiver")

    first_message = {
        "meta": {
            "id": "123",
        },
        "from": "Sender",
        "to": "Receiver",
        "action": {
            "name": "undefined_action",
        }
    }
    sender.send(first_message)
    assert_message_log(sender._message_log, [
        first_message,
        {
            "meta": {
                "parent_id": "123",
            },
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[error]",
                "args": {
                    "error": "AttributeError: \"undefined_action\" not found on \"Receiver\"",
                },
            }
        },
    ])
