from agency.agent import (ACCESS_DENIED, ACCESS_REQUESTED, action)
from tests.helpers import ObservableAgent, add_agent, assert_message_log


class _SendUnpermittedActionAgent(ObservableAgent):
    @action(access_policy=ACCESS_DENIED)
    def say(self, content: str):
        pass


def test_send_unpermitted_action(any_space):
    """Tests sending an unpermitted action and receiving an error response"""

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, _SendUnpermittedActionAgent, "Chatty")

    first_message = {
        'from': 'Webster',
        'to': 'Chatty',
        'action': {
            'name': 'say',
            'args': {
                'content': 'Hello, Chatty!'
            }
        }
    }
    any_space._route(first_message)
    assert_message_log(websters_log, [
        {
            "meta": {
                "response_id": None,
            },
            "from": "Chatty",
            "to": "Webster",
            "action": {
                "name": "response",
                "args": {
                    "error": "\"Chatty.say\" not permitted",
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
    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(
        any_space, _SendRequestPermittedActionAgent, "Chatty")

    first_message = {
        'from': 'Webster',
        'to': 'Chatty',
        'action': {
            'name': 'say',
            'args': {
                'content': 'Chatty, what is the answer to life, the universe, and everything?'
            }
        }
    }
    any_space._route(first_message)
    assert_message_log(websters_log, [
        {
            "meta": {
                "response_id": None,
            },
            "from": "Chatty",
            "to": "Webster",
            "action": {
                "name": "response",
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

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, _SendRequestReceivedActionAgent, "Chatty")

    first_message = {
        'from': 'Webster',
        'to': 'Chatty',
        'action': {
            'name': 'say',
            'args': {
                'content': 'Chatty, what is the answer to life, the universe, and everything?'
            }
        }
    }
    any_space._route(first_message)
    assert_message_log(websters_log, [
        {
            "meta": { "response_id": None },
            "from": "Chatty",
            "to": "Webster",
            "action": {
                "name": "response",
                "args": {
                    "error": "\"Chatty.say\" not permitted",
                }
            },
        },
    ])
