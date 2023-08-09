import json
import time
import pytest
from unittest.mock import MagicMock

import tracemalloc
tracemalloc.start()

from agency.agent import (ACCESS_DENIED, ACCESS_REQUESTED, Agent, action)
from agency.spaces.amqp_space import AMQPOptions, AMQPSpace
from agency.spaces.native_space import NativeSpace
from agency.util import debug


class Webster(Agent):
    """A fake agent for testing that ignores its own broadcasts by default"""
    def __init__(self, id: str, receive_own_broadcasts: bool = False):
        super().__init__(id, receive_own_broadcasts=receive_own_broadcasts)

    @action
    def say(self, content: str):
        """Use this action to say something to Webster"""

    @action
    def response(self, data, original_message_id: str):
        """Handles responses"""

    @action
    def error(self, error: str, original_message_id: str):
        """Handles errors"""


def wait_for_messages(agent, count=1, max_seconds=5):
    """
    A utility method to wait for messages to be processed. Throws an exception
    if the number of messages received goes over count, or if the timeout is
    reached.
    """
    print(f"{agent.id()} waiting {max_seconds} seconds for {count} messages...")
    start_time = time.time()
    while ((time.time() - start_time) < max_seconds):
        time.sleep(0.01)
        if len(agent._message_log) > count:
            raise Exception(
                f"too many messages received: {len(agent._message_log)} expected: {count}\n{json.dumps(agent._message_log, indent=2)}")
        if len(agent._message_log) == count:
            return
    raise Exception(
        f"too few messages received: {len(agent._message_log)} expected: {count}\n{json.dumps(agent._message_log, indent=2)}")


@pytest.fixture
def native_space():
    return NativeSpace()


@pytest.fixture
def amqp_space():
    return AMQPSpace(exchange="agency-test")


@pytest.fixture
def amqp_space_with_short_heartbeat():
    return AMQPSpace(
        amqp_options=AMQPOptions(heartbeat=2),
        exchange="agency-test",
    )


@pytest.fixture(params=['native_space', 'amqp_space'])
def either_space(request, native_space, amqp_space):
    """
    Used for tests that should be run for both NativeSpace and AMQPSpace.
    """
    space = None
    if request.param == 'native_space':
        space = native_space
    elif request.param == 'amqp_space':
        space = amqp_space

    try:
        yield space
    finally:
        space.remove_all()


# ------------------------------------------------------------------------------
# Begin tests


def test_help_action(either_space):
    """Tests defining help info, requesting it, receiving the response"""

    # Define Chatty class
    class Chatty(Agent):
        @action
        def action_with_docstring(self, content: str, number, thing: dict, foo: bool) -> dict:
            """
            A test action

            Some more description text

            Args:
                content (str): some string
                number (int): some number without the type in the signature
                thing: some object without the type in the docstring
                foo (str): some boolean with the wrong type in the docstring

            Returns:
                dict: a return value
            """

        @action(
            help={
                "something": "made up",
                "anything": {
                    "whatever": {
                        "I": "want"
                    },
                },
                "stuff": ["a", "b", "c"]
            }
        )
        def action_with_custom_help():
            """The docstring here is ignored"""

    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

    # Send the first message and wait for a response
    first_message = {
        'to': '*',  # broadcast
        'from': 'Webster',
        'action': {
            'name': 'help',
            'args': {}
        }
    }
    webster.send(first_message)
    wait_for_messages(webster, count=2)

    assert webster._message_log[0] == first_message
    assert webster._message_log[1] == { # chatty's response
        "to": "Webster",
        "from": "Chatty",
        "action": {
            "name": "response",
            "args": {
                "data": {
                    "action_with_docstring": {
                        "description": "A test action Some more description text",
                        "args": {
                            "content": {"type": "string", "description": "some string"},
                            "number": {"type": "number", "description": "some number without the type in the signature"},
                            "thing": {"type": "object", "description": "some object without the type in the docstring"},
                            "foo": {"type": "boolean", "description": "some boolean with the wrong type in the docstring"},
                        },
                        "returns": {"type": "object", "description": "a return value"}
                    },
                    "action_with_custom_help": {
                        "something": "made up",
                        "anything": {
                            "whatever": {
                                "I": "want"
                            },
                        },
                        "stuff": ["a", "b", "c"]
                    }
                },
                "original_message_id": None,
            }
        }
    }


def test_help_specific_action(either_space):
    """Tests requesting help for a specific action"""

    # Define Chatty class
    class Chatty(Agent):
        @action
        def action_i_will_request_help_on():
            pass

        @action
        def action_i_dont_care_about():
            pass

    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

    # Send the first message and wait for a response
    first_message = {
        'to': '*',  # broadcast
        'from': 'Webster',
        'action': {
            'name': 'help',
            'args': {
                'action_name': 'action_i_will_request_help_on'
            }
        }
    }
    webster.send(first_message)
    wait_for_messages(webster, count=2)

    assert webster._message_log[0] == first_message
    assert webster._message_log[1] == {
        "to": "Webster",
        "from": "Chatty",
        "action": {
            "name": "response",
            "args": {
                "data": {
                    "action_i_will_request_help_on": {
                        "args": {},
                    },
                },
                "original_message_id": None,
            }
        }
    }


def test_responses_have_original_message_id(either_space):
    """Tests that original_message_id is populated on responses and errors"""
    class Chatty(Agent):
        @action
        def say(self, content: str):
            return ["Hello!"]

    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

    # this message will result in a response with data
    first_message = {
        'id': '123 whatever i feel like here',
        'to': 'Chatty',
        'from': 'Webster',
        'action': {
            'name': 'say',
            'args': {
                'content': 'Hi Chatty!'
            }
        }
    }
    webster.send(first_message)

    wait_for_messages(webster, count=2)
    assert webster._message_log[0] == first_message
    assert webster._message_log[1] == {
        "to": "Webster",
        "from": "Chatty",
        "action": {
            "name": "response",
            "args": {
                "data": ["Hello!"],
                "original_message_id": "123 whatever i feel like here",
            }
        }
    }

def test_errors_have_original_message_id(either_space):
    """Tests that original_message_id is populated on errors"""
    class Chatty(Agent):
        pass

    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

    # this message will result in an error
    first_message = {
        'id': '456 whatever i feel like here',
        'to': 'Chatty',
        'from': 'Webster',
        'action': {
            'name': 'some non existent action',
            'args': {
                'content': 'Hi Chatty!'
            }
        }
    }
    webster.send(first_message)

    wait_for_messages(webster, count=2)
    assert webster._message_log[0] == first_message
    assert webster._message_log[1] == {
        "to": "Webster",
        "from": "Chatty",
        "action": {
            "name": "error",
            "args": {
                "error": "\"some non existent action\" not found on \"Chatty\"",
                "original_message_id": "456 whatever i feel like here",
            }
        }
    }



def test_unique_ids(either_space):
    """
    Asserts that two agents may NOT have the same id
    """
    either_space.add(Webster("Webster"))
    with pytest.raises(ValueError):
        either_space.add(Webster("Webster"))


def test_id_validation():
    """
    Asserts ids are:
    - 1 to 255 characters in length
    - Cannot start with the reserved sequence `"amq."`
    - Cannot use the reserved broadcast id "*"
    """
    # Test valid id
    valid_id = "valid_agent_id"
    agent = Agent(valid_id)
    assert agent.id() == valid_id

    # Test id length
    too_short_id = ""
    too_long_id = "a" * 256
    with pytest.raises(ValueError):
        Agent(too_short_id)
    with pytest.raises(ValueError):
        Agent(too_long_id)

    # Test reserved sequence
    reserved_id = "amq.reserved"
    with pytest.raises(ValueError):
        Agent(reserved_id)

    # Test reserved broadcast id
    reserved_broadcast_id = "*"
    with pytest.raises(ValueError):
        Agent(reserved_broadcast_id)



def test_after_add_and_before_remove(either_space):
    """
    Tests that the _after_add and _before_remove methods are called when an
    agent is added to and removed from a space.
    """
    agent = Webster("Webster")
    agent.after_add = MagicMock()
    either_space.add(agent)
    agent.after_add.assert_called_once()

    agent.before_remove = MagicMock()
    either_space.remove(agent)
    agent.before_remove.assert_called_once()


def test_before_and_after_action():
    """
    Tests the before and after action callbacks
    """
    agent = Webster("Webster")
    agent.before_action = MagicMock()
    agent.after_action = MagicMock()
    agent._receive({
        "from": "Chatty",
        "to": "Webster",
        "action": {
            "name": "say",
            "args": {
                "content": "Hello, Webster!",
            },
        }
    })
    agent.before_action.assert_called_once()
    agent.after_action.assert_called_once()


def test_self_received_broadcast(either_space):
    class Chatty(Agent):
        @action
        def say(self, content: str):
            pass

    webster = Webster("Webster", receive_own_broadcasts=True)
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

    first_message = {
        "from": "Webster",
        "to": "*",  # makes it a broadcast
        "action": {
            "name": "say",
            "args": {
                "content": "Hello, everyone!",
            },
        },
    }
    webster.send(first_message)
    wait_for_messages(webster, count=2)
    wait_for_messages(chatty, count=1)
    assert webster._message_log == [first_message, first_message]
    assert chatty._message_log == [first_message]


def test_non_self_received_broadcast(either_space):
    class Chatty(Agent):
        @action
        def say(self, content: str):
            pass

    webster = Webster("Webster", receive_own_broadcasts=False)
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

    first_message = {
        "from": "Webster",
        "to": "*",  # makes it a broadcast
        "action": {
            "name": "say",
            "args": {
                "content": "Hello, everyone!",
            },
        },
    }
    webster.send(first_message)
    wait_for_messages(webster, count=1)
    wait_for_messages(chatty, count=1)
    assert webster._message_log == [first_message]
    assert chatty._message_log == [first_message]


def test_send_and_receive(either_space):
    """Tests sending a basic "say" message receiving a "return"ed reply"""

    class Chatty(Agent):
        @action
        def say(self, content: str):
            self.send({
                "to": "Webster",
                "action": {
                    "name": "say",
                    "args": {
                        "content": f"Hello, {self._current_message['from']}!",
                    }
                }
            })

    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

    # Send the first message and wait for a response
    first_message = {
        'from': 'Webster',
        'to': chatty.id(),
        'action': {
            'name': 'say',
            'args': {
                'content': 'Hello, Chatty!'
            }
        }
    }
    webster.send(first_message)
    wait_for_messages(webster, count=2)

    assert webster._message_log == [
        first_message,
        {
            "from": "Chatty",
            "to": "Webster",
            "action": {
                "name": "say",
                "args": {
                    "content": "Hello, Webster!"
                }
            },
        },
    ]


def test_meta(either_space):
    """
    Tests that the meta field is transmitted when populated
    """
    class Chatty(Agent):
        @action
        def say(self, content: str):
            pass

    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

    first_message = {
        "meta": {
            "something": "made up",
            "foo": 0,
            "bar": ["baz"]
        },
        "from": "Webster",
        "to": "Chatty",
        "action": {
            "name": "say",
            "args": {
                "content": "Hello, Chatty!"
            }
        },
    }
    webster.send(first_message)
    wait_for_messages(chatty, count=1)
    assert chatty._message_log == [first_message]


def test_send_undefined_action(either_space):
    """Tests sending an undefined action and receiving an error response"""

    # In this test we skip defining a say action on chatty in order to test the
    # error response

    class Chatty(Agent):
        pass

    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

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
    webster.send(first_message)
    wait_for_messages(webster, count=2)

    assert webster._message_log == [
        first_message,
        {
            "from": "Chatty",
            "to": "Webster",
            "action": {
                "name": "error",
                "args": {
                    "error": "\"say\" not found on \"Chatty\"",
                    "original_message_id": None,
                },
            }
        },
    ]


def test_send_unpermitted_action(either_space):
    """Tests sending an unpermitted action and receiving an error response"""

    class Chatty(Agent):
        @action(access_policy=ACCESS_DENIED)
        def say(self, content: str):
            pass

    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

    first_message = {
        'from': 'Webster',
        'to': chatty.id(),
        'action': {
            'name': 'say',
            'args': {
                'content': 'Hello, Chatty!'
            }
        }
    }
    webster.send(first_message)
    wait_for_messages(webster, count=2)

    assert webster._message_log == [
        first_message,
        {
            "from": "Chatty",
            "to": "Webster",
            "action": {
                "name": "error",
                "args": {
                    "error": "\"Chatty.say\" not permitted",
                    "original_message_id": None,
                }
            }
        },
    ]


def test_send_request_permitted_action(either_space):
    """Tests sending an action, granting permission, and returning response"""

    class Chatty(Agent):
        @action(access_policy=ACCESS_REQUESTED)
        def say(self, content: str):
            return "42"

        def request_permission(self, proposed_message: dict) -> bool:
            return True

    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

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
    webster.send(first_message)
    wait_for_messages(webster, count=2)

    assert webster._message_log == [
        first_message,
        {
            "from": "Chatty",
            "to": "Webster",
            "action": {
                "name": "response",
                "args": {
                    "data": "42",
                    "original_message_id": None,
                }
            },
        },
    ]


def test_send_request_rejected_action(either_space):
    """Tests sending an action, rejecting permission, and returning error"""

    class Chatty(Agent):
        @action(access_policy=ACCESS_REQUESTED)
        def say(self, content: str):
            return "42"

        def request_permission(self, proposed_message: dict) -> bool:
            return False

    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

    first_message = {
        'from': 'Webster',
        'to': chatty.id(),
        'action': {
            'name': 'say',
            'args': {
                'content': 'Chatty, what is the answer to life, the universe, and everything?'
            }
        }
    }
    webster.send(first_message)
    wait_for_messages(webster, count=2)

    assert webster._message_log == [
        first_message,
        {
            "from": "Chatty",
            "to": "Webster",
            "action": {
                "name": "error",
                "args": {
                    "error": "\"Chatty.say\" not permitted",
                    "original_message_id": None,
                }
            },
        },
    ]


def test_heartbeat(amqp_space_with_short_heartbeat):
    """
    Tests the amqp heartbeat is sent by setting a short heartbeat interval and
    ensuring the connection remains open.
    """
    class Harford(Agent):
        @action
        def say(self, content: str):
            pass

    hartford = Harford("Hartford")
    amqp_space_with_short_heartbeat.add(hartford)

    # wait enough time for connection to drop if no heartbeat is sent
    time.sleep(6)  # 3 x heartbeat

    # send yourself a message
    message = {
        "from": hartford.id(),
        "to": hartford.id(),
        "action": {
            "name": "say",
            "args": {
                "content": "Hello",
            }
        },
    }
    hartford.send(message)
    wait_for_messages(hartford, count=2, max_seconds=5)

    # should receive the outgoing and incoming messages
    assert len(hartford._message_log) == 2
    assert hartford._message_log == [message, message]

    # cleanup
    amqp_space_with_short_heartbeat.remove(hartford)
