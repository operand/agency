import pytest
from agency.agent import (ACCESS_DENIED, ACCESS_REQUESTED, Agent, action)
from agency.space import Space
from tests.helpers import assert_message_log


class _SendUnpermittedActionAgent(Agent):
    @action(access_policy=ACCESS_DENIED)
    def say(self, content: str):
        pass


def test_send_unpermitted_action(any_space):
    """Tests sending an unpermitted action and receiving an error response"""

    sender = any_space.add_foreground(Agent, "Sender")
    any_space.add(_SendUnpermittedActionAgent, "Receiver")

    first_message = {
        "meta": {"id": "123"},
        "from": "Sender",
        "to": "Receiver",
        "action": {
            "name": "say",
            "args": {
                "content": "Hello, Receiver!"
            }
        }
    }
    sender.send(first_message)
    assert_message_log(sender._message_log, [
        first_message,
        {
            "meta": {"parent_id": "123"},
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[error]",
                "args": {
                    "error": "PermissionError: \"Receiver.say\" not permitted",
                }
            }
        },
    ])


class _SendRequestPermittedActionAgent(Agent):
    @action(access_policy=ACCESS_REQUESTED)
    def say(self, content: str):
        self.respond_with("42")

    def request_permission(self, proposed_message: dict) -> bool:
        return True


def test_send_permitted_action(any_space: Space):
    """Tests sending an action, granting permission, and returning response"""
    sender = any_space.add_foreground(Agent, "Sender")
    any_space.add(_SendRequestPermittedActionAgent, "Receiver")

    first_message = {
        "meta": {"id": "123"},
        "from": "Sender",
        "to": "Receiver",
        "action": {
            "name": "say",
            "args": {
                "content": "Receiver, what is the answer to life, the universe, and everything?"
            }
        }
    }
    sender.send(first_message)
    assert_message_log(sender._message_log, [
        first_message,
        {
            "meta": {"parent_id": "123"},
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "value": "42",
                }
            },
        },
    ])


class _SendRequestReceivedActionAgent(Agent):
    @action(access_policy=ACCESS_REQUESTED)
    def say(self, content: str):
        return "42"

    def request_permission(self, proposed_message: dict) -> bool:
        return False


def test_send_rejected_action(any_space):
    """Tests sending an action, rejecting permission, and returning error"""

    sender = any_space.add_foreground(Agent, "Sender")
    any_space.add(_SendRequestReceivedActionAgent, "Receiver")

    first_message = {
        "meta": {"id": "123"},
        "from": "Sender",
        "to": "Receiver",
        "action": {
            "name": "say",
            "args": {
                "content": "Receiver, what is the answer to life, the universe, and everything?"
            }
        }
    }
    sender.send(first_message)
    assert_message_log(sender._message_log, [
        first_message,
        {
            "meta": {"parent_id": "123"},
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[error]",
                "args": {
                    "error": "PermissionError: \"Receiver.say\" not permitted",
                }
            },
        },
    ])
