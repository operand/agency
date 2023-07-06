from unittest.mock import MagicMock
from agency import util
from agency.agent import (ACCESS_DENIED, ACCESS_PERMITTED,
                          ACCESS_REQUESTED, Agent, access_policy)
from agency.space import NativeSpace
import pytest
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
          "from": original_message['to'],
          "to": self.id(),
          "thoughts": "A value was returned for your action",
          "action": "say",
          "args": {
            "content": return_value.__str__(),
          },
        })

    @access_policy(ACCESS_PERMITTED)
    def _action__error(self, original_message: dict, error: str):
        self._receive({
          "from": original_message['to'],
          "to": self.id(),
          "thoughts": "An error occurred",
          "action": "say",
          "args": {
            "content": f"ERROR: {error}",
          },
        })


class Chatty(Agent):
    """A fake AI agent"""


# A utility method used by tests to wait for messages to be processed
def wait_for_messages(agent, count=1, max_seconds=2):
    start_time = time.time()
    while ((time.time() - start_time) < max_seconds):
        time.sleep(0.01)
        if len(agent._message_log) > count:
            util.debug("*", agent._message_log)
            raise Exception(
                f"too many messages received: {len(agent._message_log)} expected: {count}")
        if len(agent._message_log) == count:
            return


def parametrize_spaces(test_func):
    """
    Used for tests that should be run for both NativeSpace and AMQPSpace.
    """
    # amqp_space = AMQPSpace()
    native_space = NativeSpace()

    return pytest.mark.parametrize('space', [
        native_space,
        # amqp_space,
    ])(test_func)


def parametrize_space_with_agents(test_func):
    """
    Used for tests that should be run for both NativeSpace and AMQPSpace. This
    decorator also adds the two agents to the space: Webster and Chatty.
    """
    # amqp_space = AMQPSpace()
    # amqp_webster = Webster("Webster")
    # amqp_chatty = Chatty("Chatty")
    # amqp_space.add(amqp_webster)
    # amqp_space.add(amqp_chatty)

    native_space = NativeSpace()
    native_webster = Webster("Webster")
    native_chatty = Chatty("Chatty")
    native_space.add(native_webster)
    native_space.add(native_chatty)

    return pytest.mark.parametrize('space,webster,chatty', [
        (native_space, native_webster, native_chatty),
        # (amqp_space, amqp_webster, amqp_chatty),
    ])(test_func)


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


@parametrize_spaces
def test_after_add_and_before_remove(space):
    """
    Tests that the _after_add and _before_remove methods are called when an
    agent is added to and removed from a space.
    """
    agent = Chatty("Chatty")
    agent._after_add = MagicMock()
    space.add(agent)
    agent._after_add.assert_called_once()

    agent._before_remove = MagicMock()
    space.remove(agent)
    agent._before_remove.assert_called_once()


def test_before_and_after_action():
    """
    Tests that the _after_action method is called after an action is performed
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


@parametrize_space_with_agents
def test_agent_not_found(space, webster, chatty):
    """
    When an agent sends a message to an agent that does not exist, the sender
    should receive an error message
    """
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
            "from": "NonExistentAgent"
        },
        {
            "to": "Webster",
            "thoughts": "An error occurred",
            "action": "say",
            "args": {
                "content": "ERROR: \"NonExistentAgent\" not found"
            },
            "from": "NonExistentAgent"
        },
    ]


@parametrize_space_with_agents
def test_broadcast(space, webster, chatty):
    """
    When an agent broadcasts a message, all other agents should receive the
    message
    """
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


@parametrize_space_with_agents
def test_send_and_receive(space, webster, chatty):
    """Tests sending a basic "say" message receiving a "return"ed reply"""

    # We use callable class to dynamically define the _say action for chatty
    class ChattySay():
        def __init__(self, agent) -> None:
            self.agent = agent
            self.access_policy = ACCESS_PERMITTED

        def __call__(self, content):
            return 'Hello, Webster!'

    chatty._action__say = ChattySay(chatty)

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


@parametrize_space_with_agents
def test_send_undefined_action(space, webster, chatty):
    """Tests sending an undefined action and receiving an error response"""

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


@parametrize_space_with_agents
def test_send_unpermitted_action(space, webster, chatty):
    """Tests sending an unpermitted action and receiving an error response"""

    class ChattySay():
        def __init__(self, agent) -> None:
            self.agent = agent
            self.access_policy = ACCESS_DENIED

        def __call__(self, content):
            # Note that we are also testing the default "return" impl which converts a
            # returned value into an incoming "say" action, by returning a string here.
            return 'Hello, Webster!'

    chatty._action__say = ChattySay(chatty)

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


@parametrize_space_with_agents
def test_send_request_permitted_action(space, webster, chatty):
    """Tests sending an action, granting permission, and returning response"""

    # We use callable classes to dynamically define _action__say and
    # _request_permission
    class ChattySay():
        def __init__(self, agent) -> None:
            self.agent = agent
            self.access_policy = ACCESS_REQUESTED

        def __call__(self, content):
            return '42'

    chatty._action__say = ChattySay(chatty)

    class ChattyAsk():
        def __call__(self, proposed_message):
            return True

    chatty._request_permission = ChattyAsk()

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


@parametrize_space_with_agents
def test_send_request_rejected_action(space, webster, chatty):
    """Tests sending an action, rejecting permission, and returning error"""

    # We use callable classes to dynamically define _action__say and
    # _request_permission
    class ChattySay():
        def __init__(self, agent) -> None:
            self.agent = agent
            self.access_policy = ACCESS_REQUESTED

        def __call__(self, content):
            return '42'

    chatty._action__say = ChattySay(chatty)

    class ChattyAsk():
        def __call__(self, proposed_message):
            return False

    chatty._request_permission = ChattyAsk()

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