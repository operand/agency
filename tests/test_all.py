from agency.agent import (ACCESS_DENIED, ACCESS_PERMITTED,
                          ACCESS_REQUESTED, Agent, access_policy)
from agency.space import NativeSpace
import pytest
import time


class Webster(Agent):
    """A fake human agent that sits behind a webapp Space"""

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


class FakeWebApp():
    """A fake webapp space that Webster is an agent within"""


class Chatty(Agent):
    """A fake AI agent"""


def wait_for_messages(agent, count=1, max_seconds=2):
    start_time = time.time()
    while (
        (time.time() - start_time) < max_seconds
        and agent._message_log.__len__() < count
    ):
        time.sleep(0.1)


def space_with_webster_and_chatty():
    """
    Returns a space with a Webster agent and a Chatty agent
    """
    space = NativeSpace()
    webster = Webster("Webster")
    chatty = Chatty("Chatty")
    space.add(webster)
    space.add(chatty)

    return space, webster, chatty


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


@pytest.mark.skip
def test_after_add_and_before_remove():
    raise NotImplementedError()


@pytest.mark.skip
def test_after_action():
    raise NotImplementedError()


@pytest.mark.skip
def test_agent_not_found():
    """
    When an agent sends a message to an agent that does not exist, the sender
    should receive an error message
    """
    raise NotImplementedError()


@pytest.mark.focus
def test_send_and_receive():
    """Tests sending a basic "say" message receiving a "return"ed reply"""
    space, webster, chatty = space_with_webster_and_chatty()

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
    print(webster._message_log)
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


@pytest.mark.skip
def test_broadcast():
    raise NotImplementedError()


def test_send_undefined_action():
    """Tests sending an undefined action and receiving an error response"""
    space, webster, chatty = space_with_webster_and_chatty()

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


def test_send_unpermitted_action():
    """Tests sending an unpermitted action and receiving an error response"""
    space, webster, chatty = space_with_webster_and_chatty()

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


def test_send_request_permitted_action():
    """Tests sending an action, granting permission, and returning response"""
    space, webster, chatty = space_with_webster_and_chatty()

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


# send action -> reject -> return permission error
def test_send_request_rejected_action():
    """Tests sending an action, rejecting permission, and returning error"""
    space, webster, chatty = space_with_webster_and_chatty()

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
