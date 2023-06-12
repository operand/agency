from contextlib import contextmanager
from agency.agent import ACCESS_REQUESTED, ACCESS_DENIED, ACCESS_PERMITTED, access_policy
from agency.agent import Agent
from agency.space import Space
from tests.conftest import space_context
import time
import unittest


class Webster(Agent):
    """A fake human agent that sits behind a webapp Space"""

    @access_policy(ACCESS_PERMITTED)
    def _action__say(self, content):
        pass


class FakeWebApp(Space):
    """A fake webapp space that Webster is an agent within"""


class Chatty(Agent):
    """A fake AI agent"""


def wait_for_messages(agent, count=2):
    max_time = 2  # seconds
    start_time = time.time()
    while (
        (time.time() - start_time) < max_time
        and agent._message_log.__len__() < count
    ):
        time.sleep(0.1)


@contextmanager
def space_with_webster_and_chatty():
    """Returns a Space with a Webster agent"""
    with space_context() as space:
        chatty = Chatty("Chatty")
        # NOTE that webster is nested in the webapp space
        webster = Webster("Webster")
        webapp = FakeWebApp("TestWebApp")
        webapp.add(webster)

        space.add(webapp)
        space.add(chatty)

        yield webster, chatty


def test_send_and_receive():
    """Tests sending a basic "say" message receiving a "return"ed reply"""
    with space_with_webster_and_chatty() as (webster, chatty):

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
        wait_for_messages(webster)

        first_message = {
            'from': 'Webster.TestWebApp.TestSpace',
            **first_action
        }
        assert webster._message_log == [
            first_message,
            {
                "to": "Webster.TestWebApp.TestSpace",
                "thoughts": "A value was returned for your action",
                "action": "return",
                "args": {
                    "original_message": first_message,
                    "return_value": "Hello, Webster!"
                },
                "from": "Chatty.TestSpace"
            },
            {
                "to": "Webster.TestWebApp.TestSpace",
                "thoughts": "A value was returned for your action",
                "action": "say",
                "args": {
                    "content": "Hello, Webster!"
                },
                "from": "Chatty.TestSpace"
            },
        ]


def test_send_undefined_action():
    """Tests sending an undefined action and receiving an error response"""
    with space_with_webster_and_chatty() as (webster, chatty):

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
        wait_for_messages(webster)

        first_message = {
            'from': 'Webster.TestWebApp.TestSpace',
            **first_action,
        }
        assert webster._message_log == [
            first_message,
            {
                "to": "Webster.TestWebApp.TestSpace",
                "thoughts": "An error occurred",
                "action": "error",
                "args": {
                    "original_message": first_message,
                    "error": "\"say\" action not found"
                },
                "from": "Chatty.TestSpace"
            },
            {
                "to": "Webster.TestWebApp.TestSpace",
                "thoughts": "An error occurred",
                "action": "say",
                "args": {
                    "content": "ERROR: \"say\" action not found"
                },
                "from": "Chatty.TestSpace"
            }
        ]


def test_send_unpermitted_action():
    """Tests sending an unpermitted action and receiving an error response"""
    with space_with_webster_and_chatty() as (webster, chatty):

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
        wait_for_messages(webster)

        first_message = {
            'from': 'Webster.TestWebApp.TestSpace',
            **first_action,
        }
        assert webster._message_log == [
            first_message,
            {
                "from": "Chatty.TestSpace",
                "to": "Webster.TestWebApp.TestSpace",
                "thoughts": "An error occurred",
                "action": "error",
                "args": {
                    "original_message": first_message,
                    "error": "\"Chatty.TestSpace.say\" not permitted",
                }
            },
            {
                "to": "Webster.TestWebApp.TestSpace",
                "thoughts": "An error occurred",
                "action": "say",
                "args": {
                    "content": "ERROR: \"Chatty.TestSpace.say\" not permitted"
                },
                "from": "Chatty.TestSpace"
            }
        ]


def test_send_request_permitted_action():
    """Tests sending an action, granting permission, and returning response"""
    with space_with_webster_and_chatty() as (webster, chatty):

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
        wait_for_messages(webster)

        first_message = {
            'from': 'Webster.TestWebApp.TestSpace',
            **first_action,
        }
        assert webster._message_log == [
            first_message,
            {
                "to": "Webster.TestWebApp.TestSpace",
                "thoughts": "A value was returned for your action",
                "action": "return",
                "args": {
                    "original_message": first_message,
                    "return_value": "42"
                },
                "from": "Chatty.TestSpace"
            },
            {
                "to": "Webster.TestWebApp.TestSpace",
                "thoughts": "A value was returned for your action",
                "action": "say",
                "args": {
                    "content": "42"
                },
                "from": "Chatty.TestSpace"
            }
        ]


# send action -> reject -> return permission error
def test_send_request_rejected_action():
    """Tests sending an action, rejecting permission, and returning error"""
    with space_with_webster_and_chatty() as (webster, chatty):

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
        wait_for_messages(webster)

        first_message = {
            'from': 'Webster.TestWebApp.TestSpace',
            **first_action,
        }
        assert webster._message_log == [
            first_message,
            {
                "to": "Webster.TestWebApp.TestSpace",
                "thoughts": "An error occurred",
                "action": "error",
                "args": {
                    "original_message": first_message,
                    "error": "\"Chatty.TestSpace.say\" not permitted"
                },
                "from": "Chatty.TestSpace"
            },
            {
                "to": "Webster.TestWebApp.TestSpace",
                "thoughts": "An error occurred",
                "action": "say",
                "args": {
                    "content": "ERROR: \"Chatty.TestSpace.say\" not permitted"
                },
                "from": "Chatty.TestSpace"
            }
        ]


# TODO: test broadcasting


if __name__ == '__main__':
    unittest.main()
