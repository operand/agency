from agency import util
from agency.agent import (ACCESS_DENIED, ACCESS_PERMITTED,
                          ACCESS_REQUESTED, Agent, access_policy)
from agency.space import AMQPSpace, NativeSpace
from unittest.mock import MagicMock
import pika
import pytest
import pytest_asyncio
import time


class Webster(Agent):
    """A fake human agent"""

    @access_policy(ACCESS_PERMITTED)
    def _action__say(self, content):
        pass

    # We implement actions for "return" and "error" so that we can test that
    # these are called correctly as well. They simply forward the messages as
    # "say" messages to the original sender (Webster)
    @access_policy(ACCESS_PERMITTED)
    def _action__return(self, original_message: dict, return_value: str):
        self._receive({
          "from": self._current_message['from'],
          "to": self._current_message['to'],
          "thoughts": "A value was returned for your action",
          "action": "say",
          "args": {
            "content": return_value.__str__(),
          },
        })

    @access_policy(ACCESS_PERMITTED)
    def _action__error(self, original_message: dict, error: str):
        self._receive({
          "from": self._current_message['from'],
          "to": self._current_message['to'],
          "thoughts": "An error occurred",
          "action": "say",
          "args": {
            "content": f"ERROR: {error}",
          },
        })


class Chatty(Agent):
    """A fake AI agent"""


def wait_for_messages(agent, count=1, max_seconds=3):
    """
    A utility method to wait for messages to be processed. Throws an exception
    if the number of messages received goes over count.
    """
    start_time = time.time()
    while ((time.time() - start_time) < max_seconds):
        time.sleep(0.01)
        if len(agent._message_log) > count:
            raise Exception(
                f"too many messages received: {len(agent._message_log)} expected: {count}")
        if len(agent._message_log) == count:
            return


@pytest.fixture
def native_space():
    return NativeSpace()


@pytest.fixture
def amqp_space():
    connection_params = pika.ConnectionParameters(
        host='localhost',
        port='5672',
        credentials=pika.PlainCredentials(
            'guest', 'guest'
        ),
    )
    return AMQPSpace(pika_connection_params=connection_params)


@pytest.fixture(params=['native_space', 'amqp_space'])
def either_space(request, native_space, amqp_space):
    if request.param == 'native_space':
        return native_space
    elif request.param == 'amqp_space':
        return amqp_space


@pytest_asyncio.fixture
async def webster_and_chatty(either_space):
    """
    Used for tests that should be run for both NativeSpace and AMQPSpace. This
    decorator also adds the two agents to the space: Webster and Chatty.
    """
    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    either_space.add(webster)
    either_space.add(chatty)

    # wait for both agents to be added
    start_time = time.time()
    while webster._space is None \
            or chatty._space is None \
            and (time.time() - start_time) < 5:
        time.sleep(0.01)

    yield (webster, chatty)

    either_space.remove(webster)
    either_space.remove(chatty)
    # wait for both agents to be removed
    start_time = time.time()
    while webster._space is not None \
            or chatty._space is not None \
            and (time.time() - start_time) < 5:
        time.sleep(0.01)


# -----------
# Begin tests
# -----------


def test_id_validation():
    """
    Asserts ids are:
    - 1 to 255 characters in length
    - Cannot start with the reserved sequence `"amq."`
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


def test_after_add_and_before_remove(either_space):
    """
    Tests that the _after_add and _before_remove methods are called when an
    agent is added to and removed from a space.
    """
    agent = Chatty("Chatty")
    agent._after_add = MagicMock()
    either_space.add(agent)
    # wait for 5 secs until ._space is set
    start_time = time.time()
    while agent._space is None and (time.time() - start_time) < 5:
        time.sleep(0.01)
    agent._after_add.assert_called_once()

    agent._before_remove = MagicMock()
    either_space.remove(agent)
    # wait for 5 secs until ._space is unset
    start_time = time.time()
    while agent._space is not None and (time.time() - start_time) < 5:
        time.sleep(0.01)
    agent._before_remove.assert_called_once()


def test_before_and_after_action():
    """
    Tests the before and after action callbacks
    """
    agent = Webster("Webster")
    agent._before_action = MagicMock()
    agent._after_action = MagicMock()
    agent._receive({
        "from": "Chatty",
        "to": "Webster",
        "thoughts": "I wonder how Chatty is doing.",
        "action": "say",
        "args": {
            "content": "Hello, Webster!",
        },
    })
    agent._before_action.assert_called_once()
    agent._after_action.assert_called_once()


def test_agent_not_found(webster_and_chatty):
    """
    When an agent sends a message to an agent that does not exist, the sender
    should receive an error message
    """
    webster, chatty = webster_and_chatty
    first_message = {
        "from": "Webster",
        "to": "NonExistentAgent",
        "thoughts": "I wonder how NonExistentAgent is doing.",
        "action": "say",
        "args": {
            "content": "Hello, NonExistentAgent!",
        },
    }
    webster._send(first_message)
    wait_for_messages(webster, count=3)
    assert webster._message_log == [
        first_message,
        {
            "to": "Webster",
            "thoughts": "An error occurred",
            "action": "error",
            "args": {
                "original_message": first_message,
                "error": "\"NonExistentAgent\" not found"
            },
            "from": "Webster"
        },
        {
            "to": "Webster",
            "thoughts": "An error occurred",
            "action": "say",
            "args": {
                "content": "ERROR: \"NonExistentAgent\" not found"
            },
            "from": "Webster"
        },
    ]


def test_broadcast(webster_and_chatty):
    """
    When an agent broadcasts a message, all other agents should receive the
    message
    """
    webster, chatty = webster_and_chatty
    chatty._action__say = MagicMock()
    chatty._action__say.access_policy = ACCESS_PERMITTED
    chatty._action__say.return_value = None

    first_message = {
        "to": None,  # makes it a broadcast
        "from": "Webster",
        "thoughts": "I wonder how everyone is doing.",
        "action": "say",
        "args": {
            "content": "Hello, everyone!",
        },
    }
    webster._send(first_message)
    wait_for_messages(webster, count=1)
    wait_for_messages(chatty, count=1)
    assert webster._message_log == [first_message]
    assert chatty._message_log == [first_message]


def test_send_and_receive(webster_and_chatty):
    """Tests sending a basic "say" message receiving a "return"ed reply"""
    webster, chatty = webster_and_chatty

    # Using MagicMock
    chatty._action__say = MagicMock()
    chatty._action__say.access_policy = ACCESS_PERMITTED
    chatty._action__say.return_value = 'Hello, Webster!'

    # Send the first message and wait for a response
    first_action = {
        'action': 'say',
        'to': chatty.id(),
        'thoughts': 'I wonder how Chatty is doing.',
        'args': {
            'content': 'Hello, Chatty!'
        }
    }
    webster._send(first_action)
    wait_for_messages(webster, count=3)

    first_message = {
        'from': 'Webster',
        **first_action
    }
    assert webster._message_log == [
        first_message,
        {
            "to": "Webster",
            "thoughts": "A value was returned for your action",
            "action": "return",
            "args": {
                "original_message": first_message,
                "return_value": "Hello, Webster!"
            },
            "from": "Chatty"
        },
        {
            "to": "Webster",
            "thoughts": "A value was returned for your action",
            "action": "say",
            "args": {
                "content": "Hello, Webster!"
            },
            "from": "Chatty"
        },
    ]


def test_send_undefined_action(webster_and_chatty):
    """Tests sending an undefined action and receiving an error response"""
    webster, chatty = webster_and_chatty

    # In this test we skip defining a _say action on chatty in order to test the
    # error response

    first_action = {
        'action': 'say',
        'to': chatty.id(),
        'thoughts': 'I wonder how Chatty is doing.',
        'args': {
            'content': 'Hello, Chatty!'
        }
    }
    webster._send(first_action)
    wait_for_messages(webster, count=3)

    first_message = {
        'from': 'Webster',
        **first_action,
    }
    assert webster._message_log == [
        first_message,
        {
            "to": "Webster",
            "thoughts": "An error occurred",
            "action": "error",
            "args": {
                "original_message": first_message,
                "error": "\"say\" action not found on \"Chatty\""
            },
            "from": "Chatty"
        },
        {
            "to": "Webster",
            "thoughts": "An error occurred",
            "action": "say",
            "args": {
                "content": "ERROR: \"say\" action not found on \"Chatty\""
            },
            "from": "Chatty"
        }
    ]


def test_send_unpermitted_action(webster_and_chatty):
    """Tests sending an unpermitted action and receiving an error response"""
    webster, chatty = webster_and_chatty

    chatty._action__say = MagicMock()
    chatty._action__say.access_policy = ACCESS_DENIED
    chatty._action__say.return_value = 'Hello, Webster!'

    first_action = {
        'action': 'say',
        'to': chatty.id(),
        'thoughts': 'I wonder how Chatty is doing.',
        'args': {
            'content': 'Hello, Chatty!'
        }
    }
    webster._send(first_action)
    wait_for_messages(webster, count=3)

    first_message = {
        'from': 'Webster',
        **first_action,
    }
    assert webster._message_log == [
        first_message,
        {
            "from": "Chatty",
            "to": "Webster",
            "thoughts": "An error occurred",
            "action": "error",
            "args": {
                "original_message": first_message,
                "error": "\"Chatty.say\" not permitted",
            }
        },
        {
            "to": "Webster",
            "thoughts": "An error occurred",
            "action": "say",
            "args": {
                "content": "ERROR: \"Chatty.say\" not permitted"
            },
            "from": "Chatty"
        }
    ]


def test_send_request_permitted_action(webster_and_chatty):
    """Tests sending an action, granting permission, and returning response"""
    webster, chatty = webster_and_chatty

    chatty._action__say = MagicMock()
    chatty._action__say.access_policy = ACCESS_REQUESTED
    chatty._action__say.return_value = '42'

    chatty._request_permission = MagicMock()
    chatty._request_permission.return_value = True

    first_action = {
        'action': 'say',
        'to': chatty.id(),
        'thoughts': 'hmmmm',
        'args': {
            'content': 'Chatty, what is the answer to life, the universe, and everything?'
        }
    }
    webster._send(first_action)
    wait_for_messages(webster, count=3)

    first_message = {
        'from': 'Webster',
        **first_action,
    }
    assert webster._message_log == [
        first_message,
        {
            "to": "Webster",
            "thoughts": "A value was returned for your action",
            "action": "return",
            "args": {
                "original_message": first_message,
                "return_value": "42"
            },
            "from": "Chatty"
        },
        {
            "to": "Webster",
            "thoughts": "A value was returned for your action",
            "action": "say",
            "args": {
                "content": "42"
            },
            "from": "Chatty"
        }
    ]


def test_send_request_rejected_action(webster_and_chatty):
    """Tests sending an action, rejecting permission, and returning error"""
    webster, chatty = webster_and_chatty

    chatty._action__say = MagicMock()
    chatty._action__say.access_policy = ACCESS_REQUESTED
    chatty._action__say.return_value = '42'

    chatty._request_permission = MagicMock()
    chatty._request_permission.return_value = False

    first_action = {
        'action': 'say',
        'to': chatty.id(),
        'thoughts': 'hmmmm',
        'args': {
            'content': 'Chatty, what is the answer to life, the universe, and everything?'
        }
    }
    webster._send(first_action)
    wait_for_messages(webster, count=3)

    first_message = {
        'from': 'Webster',
        **first_action,
    }
    assert webster._message_log == [
        first_message,
        {
            "to": "Webster",
            "thoughts": "An error occurred",
            "action": "error",
            "args": {
                "original_message": first_message,
                "error": "\"Chatty.say\" not permitted"
            },
            "from": "Chatty"
        },
        {
            "to": "Webster",
            "thoughts": "An error occurred",
            "action": "say",
            "args": {
                "content": "ERROR: \"Chatty.say\" not permitted"
            },
            "from": "Chatty"
        }
    ]
