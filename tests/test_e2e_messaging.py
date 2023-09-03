import pytest
from agency.agent import action
from tests.helpers import ObservableAgent, add_agent, assert_message_log


class _MessagingTestAgent(ObservableAgent):
    @action
    def say(self, content: str):
        """This implementation does nothing"""

    @action
    def say_with_say(self, content: str):
        self.send({
            "to": "Sender",
            "action": {
                "name": "say",
                "args": {
                    "content": f"Hello, {self._current_message()['from']}!",
                }
            }
        })

    @action
    def say_with_return(self, content: str):
        return ["Hello!"]


def test_send_and_receive_say(any_space):
    """Tests sending a basic "say" message and receiving one back"""
    senders_log = add_agent(any_space, _MessagingTestAgent, "Sender")
    receivers_log = add_agent(any_space, _MessagingTestAgent, "Receiver")

    # Send the first message and wait for a response
    first_message = {
        'from': 'Sender',
        'to': 'Receiver',
        'action': {
            'name': 'say_with_say',
            'args': {
                'content': 'Hello, Receiver!'
            }
        }
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [
        {
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "say",
                "args": {
                    "content": "Hello, Sender!"
                }
            },
        },
    ])


def test_send_and_return(any_space):
    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, _MessagingTestAgent, "Receiver")

    first_message = {
        'meta': {
            "id": "123 whatever i feel like here"
        },
        'to': 'Receiver',
        'from': 'Sender',
        'action': {
            'name': 'say_with_return',
            'args': {
                'content': 'Hi Receiver!'
            }
        }
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [{
        "meta": {
            "response_id": "123 whatever i feel like here",
        },
        "to": "Sender",
        "from": "Receiver",
        "action": {
            "name": "response",
            "args": {
                "value": ["Hello!"],
            }
        }
    }])


def test_send_and_error(any_space):
    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, ObservableAgent, "Receiver")

    # this message will result in an error
    any_space._route({
        'meta': {
            'id': '456 whatever i feel like here',
        },
        'to': 'Receiver',
        'from': 'Sender',
        'action': {
            'name': 'some non existent action',
            'args': {
                'content': 'Hi Receiver!'
            }
        }
    })

    assert_message_log(senders_log, [{
        "meta": {
            "response_id": "456 whatever i feel like here",
        },
        "to": "Sender",
        "from": "Receiver",
        "action": {
            "name": "response",
            "args": {
                "error": "\"some non existent action\" not found on \"Receiver\"",
            }
        }
    }])


class _SendingAgent(ObservableAgent):
    def after_add(self):
        return_value = self.request({
            'to': 'Receiver',
            'action': {
                'name': 'say_with_return',
                'args': {
                    'content': 'Hi Receiver!'
                }
            }
        })
        # we place the return value on the message log so we can inspect it in
        # the test
        self._message_log.append(return_value)


@pytest.mark.focus
def test_request_and_return(any_space):
    receivers_log = add_agent(any_space, _MessagingTestAgent, "Receiver")
    senders_log = add_agent(any_space, _SendingAgent, "Sender")

    first_message = {
        'meta': {
            "id": "123 whatever i feel like here"
        },
        'to': 'Receiver',
        'from': 'Sender',
        'action': {
            'name': 'say_with_return',
            'args': {
                'content': 'Hi Receiver!'
            }
        }
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [
        {
            "meta": {
                "response_id": "123 whatever i feel like here",
            },
            "to": "Sender",
            "from": "Receiver",
            "action": {
                "name": "response",
                "args": {
                    "value": ["Hello!"],
                }
            }
        },
        ["Hello!"],
    ])


@pytest.mark.skip
def test_request_and_error(any_space):
    raise NotImplementedError


def test_self_received_broadcast(any_space):
    senders_log = add_agent(any_space, ObservableAgent,
                             "Sender", receive_own_broadcasts=True)
    receivers_log = add_agent(any_space, ObservableAgent, "Receiver")
    first_message = {
        "from": "Sender",
        "to": "*",  # makes it a broadcast
        "action": {
            "name": "say",
            "args": {
                "content": "Hello, everyone!",
            },
        },
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [first_message])
    assert_message_log(receivers_log, [first_message])


def test_non_self_received_broadcast(any_space):
    senders_log = add_agent(any_space, ObservableAgent, "Sender",
                             receive_own_broadcasts=False)
    receivers_log = add_agent(
        any_space, ObservableAgent, "Receiver")

    first_message = {
        "from": "Sender",
        "to": "*",  # makes it a broadcast
        "action": {
            "name": "say",
            "args": {
                "content": "Hello, everyone!",
            },
        },
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [])
    assert_message_log(receivers_log, [first_message])


def test_meta(any_space):
    """
    Tests that the meta field is transmitted
    """

    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, _MessagingTestAgent, "Receiver")

    first_message = {
        "meta": {
            "something": "made up",
            "foo": 0,
            "bar": ["baz"]
        },
        "from": "Sender",
        "to": "Receiver",
        "action": {
            "name": "say",
            "args": {
                "content": "Hello, Receiver!"
            }
        },
    }
    any_space._route(first_message)
    assert_message_log(receivers_log, [first_message])


def test_send_undefined_action(any_space):
    """Tests sending an undefined action and receiving an error response"""

    # In this test we skip defining a say action on receiver in order to test the
    # error response

    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, ObservableAgent, "Receiver")

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
                "name": "response",
                "args": {
                    "error": "\"say\" not found on \"Receiver\"",
                },
            }
        },
    ])
