import re
import time

from agency.agent import ActionError, action
from tests.helpers import (ObservableAgent, add_agent, assert_message_log,
                           wait_for_length)


class _MessagingTestAgent(ObservableAgent):
    @action
    def null_action(self, *args, **kwargs):
        """
        This action does nothing. It accepts any arguments for convenience.
        """

    @action
    def sleep_action(self):
        time.sleep(10)

    @action
    def action_with_send(self):
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
    def action_with_return(self):
        return ["Hello!"]

    @action
    def action_with_error(self):
        raise ValueError("Something went wrong")


def test_send_and_reply(any_space):
    """Tests sending/receiving a basic send()"""
    senders_log = add_agent(any_space, _MessagingTestAgent, "Sender")
    receivers_log = add_agent(any_space, _MessagingTestAgent, "Receiver")

    # Send the first message and wait for a response
    first_message = {
        "from": "Sender",
        "to": "Receiver",
        "action": {
            "name": "action_with_send",
        }
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [
        {
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


def test_send_and_return(any_space):
    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, _MessagingTestAgent, "Receiver")

    first_message = {
        "meta": {
            "id": "123 whatever i feel like here"
        },
        "to": "Receiver",
        "from": "Sender",
        "action": {
            "name": "action_with_return",
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
            "name": "[response]",
            "args": {
                "value": ["Hello!"],
            }
        }
    }])


def test_send_and_error(any_space):
    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, _MessagingTestAgent, "Receiver")

    # this message will result in an error
    any_space._route({
        "meta": {
            "id": "456 whatever i feel like here",
        },
        "to": "Receiver",
        "from": "Sender",
        "action": {
            "name": "action_with_error",
        }
    })

    assert_message_log(senders_log, [{
        "meta": { "response_id": "456 whatever i feel like here" },
        "to": "Sender",
        "from": "Receiver",
        "action": {
            "name": "[response]",
            "args": {
                "error": "ValueError: Something went wrong",
            }
        }
    }])


class _RequestingAgent(ObservableAgent):
    @action
    def do_request(self):
        return_value = self.request({
            "to": "Responder",
            "action": {
                "name": "action_with_return",
            }
        })
        # we place the return value on the message log as a small hack so we can
        # inspect it in the test
        self._message_log.append(return_value)


def test_request_and_return(any_space):
    requesters_log = add_agent(any_space, _RequestingAgent, "Requester")
    responders_log = add_agent(any_space, _MessagingTestAgent, "Responder")

    # send a message to the requester first to kick off the request/response
    first_message = {
        "from": "Responder",
        "to": "Requester",
        "action": {
            "name": "do_request",
        }
    }
    any_space._route(first_message)
    wait_for_length(requesters_log, 4)
    requesters_log = list(requesters_log)
    # first remove dynamic meta fields and assert they are correct
    request_id = requesters_log[1]["meta"].pop("request_id")
    response_id = requesters_log[2]["meta"].pop("response_id")
    assert re.match(r"^request--.+$", request_id)
    assert response_id == request_id
    assert requesters_log == [
        first_message,
        {
            "meta": {},
            "from": "Requester",
            "to": "Responder",
            "action": {
                "name": "action_with_return",
            }
        },
        {
            "meta": {},
            "from": "Responder",
            "to": "Requester",
            "action": {
                "name": "[response]",
                "args": {
                    "value": ["Hello!"],
                }
            }
        },
        ["Hello!"],
    ]


class _RequestAndErrorAgent(ObservableAgent):
    @action
    def do_request(self):
        try:
            return_value = self.request({
                "to": "Responder",
                "action": {
                    "name": "some non existent action",
                }
            })
        except Exception as e:
            # we place the exception on the message log as a small hack so we can
            # inspect it in the test
            self._message_log.append(e)


def test_request_and_error(any_space):
    requesters_log = add_agent(any_space, _RequestAndErrorAgent, "Requester")
    responders_log = add_agent(any_space, _MessagingTestAgent, "Responder")

    # send a message to the requester first to kick off the request/response
    first_message = {
        "from": "Responder",
        "to": "Requester",
        "action": {
            "name": "do_request",
        }
    }
    any_space._route(first_message)
    wait_for_length(requesters_log, 4)
    requesters_log = list(requesters_log)
    # first remove dynamic meta fields and assert their pattern
    request_id = requesters_log[1]["meta"].pop("request_id")
    response_id = requesters_log[2]["meta"].pop("response_id")
    assert re.match(r"^request--.+$", request_id)
    assert response_id == request_id
    # assert each message one by one
    assert requesters_log[0] == first_message
    assert requesters_log[1] == {
        "meta": {},
        "from": "Requester",
        "to": "Responder",
        "action": {
            "name": "some non existent action",
        }
    }
    assert requesters_log[2] == {
        "meta": {},
        "from": "Responder",
        "to": "Requester",
        "action": {
            "name": "[response]",
            "args": {
                "error": "AttributeError: \"some non existent action\" not found on \"Responder\"",
            }
        }
    }
    assert type(requesters_log[3]) == ActionError
    assert requesters_log[3].__str__(
    ) == "AttributeError: \"some non existent action\" not found on \"Responder\""


class _RequestAndTimeoutAgent(ObservableAgent):
    @action
    def do_request(self):
        try:
            return_value = self.request({
                "to": "Responder",
                "action": {
                    "name": "sleep_action",  # sleep_action waits for a long time
                }
            })
        except TimeoutError as e:
            # we place the exception on the message log as a small hack so we can
            # inspect it in the test
            self._message_log.append(e)


def test_request_and_timeout(any_space):
    requesters_log = add_agent(any_space, _RequestAndTimeoutAgent, "Requester")
    responders_log = add_agent(any_space, _MessagingTestAgent, "Responder")

    # send a message to the requester first to kick off the request/response
    first_message = {
        "from": "Responder",
        "to": "Requester",
        "action": {
            "name": "do_request",
        }
    }
    any_space._route(first_message)
    wait_for_length(requesters_log, 3, max_seconds=5)
    requesters_log = list(requesters_log)
    # first remove dynamic meta fields and assert their pattern
    assert re.match(r"^request--.+$", requesters_log[1]["meta"].pop("request_id"))
    # assert each message one by one
    assert requesters_log[0] == first_message
    assert requesters_log[1] == {
        "meta": {},
        "from": "Requester",
        "to": "Responder",
        "action": {
            "name": "sleep_action",
        }
    }
    assert type(requesters_log[2]) == TimeoutError


def test_self_received_broadcast(any_space):
    senders_log = add_agent(any_space, ObservableAgent,
                            "Sender", receive_own_broadcasts=True)
    receivers_log = add_agent(any_space, ObservableAgent, "Receiver")
    first_message = {
        "from": "Sender",
        "to": "*",  # makes it a broadcast
        "action": {
            "name": "null_action",
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
            "name": "null_action",
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
            "name": "null_action",
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
        "from": "Sender",
        "to": "Receiver",
        "action": {
            "name": "undefined_action",
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
                    "error": "AttributeError: \"undefined_action\" not found on \"Receiver\"",
                },
            }
        },
    ])
