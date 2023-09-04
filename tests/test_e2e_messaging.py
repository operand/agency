import pytest
from agency.agent import action
from agency.util import debug
from tests.helpers import ObservableAgent, add_agent, assert_message_log, wait_for_length


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
    def action_with_return(self):
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
            'name': 'action_with_return',
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


class _RequestingAgent(ObservableAgent):
    @action
    def do_request(self):
        return_value = self.request({
            'to': 'Responder',
            'action': {
                'name': 'action_with_return',
            }
        })
        # we place the return value on the message log as a small hack so we can
        # inspect it in the test
        self._message_log.append(return_value)
        debug(f"requester logged return value", return_value)


def test_request_and_return(any_space):
    requesters_log = add_agent(any_space, _RequestingAgent, "Requester")
    responders_log = add_agent(any_space, _MessagingTestAgent, "Responder")

    # send a message to the requester first to kick off the request/response
    first_message = {
        'from': 'Responder',
        'to': 'Requester',
        'action': {
            'name': 'do_request',
        }
    }
    any_space._route(first_message)
    wait_for_length(requesters_log, 4)
    requesters_log = list(requesters_log)
    # remove dynamic meta fields. we assert they're presence by doing this
    requesters_log[1].pop("meta")
    requesters_log[2].pop("meta")
    assert requesters_log == [
        first_message,
        {
            'from': 'Requester',
            'to': 'Responder',
            'action': {
                'name': 'action_with_return',
            }
        },
        {
            "from": "Responder",
            "to": "Requester",
            "action": {
                "name": "response",
                "args": {
                    "value": ["Hello!"],
                }
            }
        },
        ["Hello!"],
    ]


@pytest.mark.skip
def test_request_and_error(any_space):
    raise NotImplementedError


@pytest.mark.skip
def test_request_and_timeout(any_space):
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
    """Tests that the meta field is transmitted"""

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
