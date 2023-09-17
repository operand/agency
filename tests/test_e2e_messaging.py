import time

import pytest

from agency.agent import action
from tests.helpers import ObservableAgent, add_agent, assert_message_log, wait_for_messages


class _MessagingTestAgent(ObservableAgent):
    @action
    def null_action(self, *args, **kwargs):
        """
        This action does nothing. It accepts any arguments for convenience.
        """

    @action
    def slow_action(self):
        """This action sleeps for 10 seconds"""
        time.sleep(10)

    @action
    def action_with_send(self):
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
        "meta": {
            "id": "123"
        },
        "from": "Sender",
        "to": "Receiver",
        "action": {
            "name": "action_with_send",
        }
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [
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
        {
            # value response when sender receives reply
            "meta": {},
            "from": "Sender",
            "to": "Receiver",
            "action": {
                "name": "[response]",
                "args": {
                    "value": None
                }
            },
        },
        {
            # value response when receiver receives original message
            "meta": {
                "parent_id": "123"
            },
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "value": None
                }
            }
        },
    ], ignore_order=True)


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
        "meta": {"parent_id": "456 whatever i feel like here"},
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
            "to": "Receiver",
            "action": {
                "name": "action_with_return",
            }
        })
        # we place the return value on the message log as a small hack so we can
        # inspect it in the test
        self._message_log.append({"return_value": return_value})


def test_request_and_return(any_space):
    senders_log = add_agent(any_space, _RequestingAgent, "Sender")
    receivers_log = add_agent(any_space, _MessagingTestAgent, "Receiver")

    # send a message to the sender first to kick off the request/response
    first_message = {
        "meta": {
            "id": "123",
        },
        "from": "Receiver",
        "to": "Sender",
        "action": {
            "name": "do_request",
        }
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [
        first_message,
        {
            "meta": {},
            "from": "Sender",
            "to": "Receiver",
            "action": {
                "name": "action_with_return",
            }
        },
        {
            "meta": {},
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "value": ["Hello!"],
                }
            }
        },
        {"return_value": ["Hello!"]},  # inserted by the agent, see above
        {
          "meta": {
            "parent_id": "123"
          },
          "to": "Receiver",
          "action": {
            "name": "[response]",
            "args": {
              "value": None,
            }
          },
          "from": "Sender"
        }
    ])


class _RequestAndErrorAgent(ObservableAgent):
    @action
    def do_request(self):
        try:
            return_value = self.request({
                "to": "Receiver",
                "action": {
                    "name": "some non existent action",
                }
            })
        except Exception as e:
            # we place the exception on the message log as a small hack so we can
            # inspect it in the test
            self._message_log.append({"error": f"{e.__class__.__name__}: {e}"})


def test_request_and_error(any_space):
    senders_log = add_agent(any_space, _RequestAndErrorAgent, "Sender")
    receivers_log = add_agent(any_space, _MessagingTestAgent, "Receiver")

    # send a message to the sender first to kick off the request/response
    first_message = {
        "meta": {
            "id": "123",
        },
        "from": "Receiver",
        "to": "Sender",
        "action": {
            "name": "do_request",
        }
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [
        first_message,
        {
            "meta": {},
            "from": "Sender",
            "to": "Receiver",
            "action": {
                "name": "some non existent action",
            }
        },
        {
            "meta": {},
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "error": "AttributeError: \"some non existent action\" not found on \"Receiver\"",
                }
            }
        },
        {
            "error": "ActionError: AttributeError: \"some non existent action\" not found on \"Receiver\""
        },
        {
            "meta": {
                "parent_id": "123"
            },
            "to": "Receiver",
            "action": {
                "name": "[response]",
                "args": {
                    "value": None
                }
            },
            "from": "Sender"
        }
    ])


class _RequestAndTimeoutAgent(ObservableAgent):
    @action
    def do_request(self):
        try:
            return_value = self.request({
                "to": "Receiver",
                "action": {
                    "name": "slow_action",
                }
            }, timeout=1)
        except TimeoutError as e:
            # we place the exception on the message log as a small hack so we can
            # inspect it in the test
            self._message_log.append({"error": f"{e.__class__.__name__}: {e}"})


def test_request_and_timeout(any_space):
    senders_log = add_agent(any_space, _RequestAndTimeoutAgent, "Sender")
    receivers_log = add_agent(any_space, _MessagingTestAgent, "Receiver")

    # send a message to the sender first to kick off the request/response
    first_message = {
        "meta": {
            "id": "123",
        },
        "from": "Receiver",
        "to": "Sender",
        "action": {
            "name": "do_request",
        }
    }
    any_space._route(first_message)
    assert_message_log(senders_log, [
        first_message,
        {
            "meta": {},
            "from": "Sender",
            "to": "Receiver",
            "action": {
                "name": "slow_action",
            }
        },
        {
            "error": "TimeoutError: "
        },
        {
            "meta": {
                "parent_id": "123"
            },
            "to": "Receiver",
            "action": {
                "name": "[response]",
                "args": {
                    "value": None,
                }
            },
            "from": "Sender",
        }
    ], max_seconds=3)  # wait enough time for the timeout


def test_self_received_broadcast_from_sender(any_space):
    senders_log = add_agent(any_space, ObservableAgent,
                            "Sender", receive_own_broadcasts=True)
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
    any_space._route(first_message)
    assert_message_log(senders_log, [
        first_message,  # self receipt of broadcast
        {
            # senders response (to itself) upon sending
            "meta": {"parent_id": "123"},
            "from": "Sender",
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "value": None
                }
            },
        },
        {
            # senders response (to itself) upon receiving
            "meta": {"parent_id": "123"},
            "from": "Sender",
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "value": None
                }
            }
        },
    ])


def test_self_received_broadcast_from_receiver(any_space):
    senders_log = add_agent(any_space, ObservableAgent,
                            "Sender", receive_own_broadcasts=True)
    receivers_log = add_agent(any_space, ObservableAgent, "Receiver")
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
    any_space._route(first_message)
    assert_message_log(receivers_log, [
        first_message,  # receipt of bcast
        {
            # receivers response to bcast
            "meta": {"parent_id": "123"},
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "value": None,
                }
            },
        }
    ])


def test_non_self_received_broadcast(any_space):
    senders_log = add_agent(any_space, ObservableAgent, "Sender",
                            receive_own_broadcasts=False)
    receivers_log = add_agent(
        any_space, ObservableAgent, "Receiver")

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
    any_space._route(first_message)
    assert_message_log(senders_log, [
        {
            # receivers response to bcast
            "meta": {
                "parent_id": "123"
            },
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "value": None
                }
            }
        }
    ])
    assert_message_log(receivers_log, [
        first_message,  # initial bcast
        {
            # receivers response to bcast
            "meta": {
                "parent_id": "123"
            },
            "from": "Receiver",
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "value": None
                }
            }
        }
    ])


def test_meta(any_space):
    """Tests the meta field"""

    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, _MessagingTestAgent, "Receiver")

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
    any_space._route(first_message)
    assert_message_log(receivers_log, [
        first_message,  # asserts receiving the meta unchanged
        {
            # response
            "meta": {
                "parent_id": "123"
            },
            "to": "Sender",
            "action": {
                "name": "[response]",
                "args": {
                    "value": None,
                }
            },
            "from": "Receiver"
        }
    ])


def test_send_undefined_action(any_space):
    """Tests sending an undefined action and receiving an error response"""

    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, ObservableAgent, "Receiver")

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
    any_space._route(first_message)
    assert_message_log(senders_log, [
        {
            "meta": {
                "parent_id": "123",
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
