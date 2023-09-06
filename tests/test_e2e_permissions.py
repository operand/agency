from agency.agent import (ACCESS_DENIED, ACCESS_REQUESTED, action)
from tests.helpers import ObservableAgent, add_agent, assert_message_log


class _SendUnpermittedActionAgent(ObservableAgent):
    @action(access_policy=ACCESS_DENIED)
    def say(self, content: str):
        pass


def test_send_unpermitted_action(any_space):
    """Tests sending an unpermitted action and receiving an error response"""

    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, _SendUnpermittedActionAgent, "Receiver")

    first_message = {
        'from': 'Sender',
        'to': 'Receiver',
        'action': {
            'name': 'say',
            'args': {
                'content': 'Hello, Receiver!'
            }
        }
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [
        {
            "meta": {
                "response_id": None,
            },
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "error": "PermissionError: \"Receiver.say\" not permitted",
                }
            }
        },
    ])


class _SendRequestPermittedActionAgent(ObservableAgent):
    @action(access_policy=ACCESS_REQUESTED)
    def say(self, content: str):
        return "42"

    def request_permission(self, proposed_message: dict) -> bool:
        return True


def test_send_request_permitted_action(any_space):
    """Tests sending an action, granting permission, and returning response"""
    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(
        any_space, _SendRequestPermittedActionAgent, "Receiver")

    first_message = {
        'from': 'Sender',
        'to': 'Receiver',
        'action': {
            'name': 'say',
            'args': {
                'content': 'Receiver, what is the answer to life, the universe, and everything?'
            }
        }
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [
        {
            "meta": {
                "response_id": None,
            },
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


class _SendRequestReceivedActionAgent(ObservableAgent):
    @action(access_policy=ACCESS_REQUESTED)
    def say(self, content: str):
        return "42"

    def request_permission(self, proposed_message: dict) -> bool:
        return False


def test_send_request_rejected_action(any_space):
    """Tests sending an action, rejecting permission, and returning error"""

    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, _SendRequestReceivedActionAgent, "Receiver")

    first_message = {
        'from': 'Sender',
        'to': 'Receiver',
        'action': {
            'name': 'say',
            'args': {
                'content': 'Receiver, what is the answer to life, the universe, and everything?'
            }
        }
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [
        {
            "meta": { "response_id": None },
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "error": "PermissionError: \"Receiver.say\" not permitted",
                }
            },
        },
    ])
