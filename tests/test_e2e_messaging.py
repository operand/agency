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
            "to": "Webster",
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
    websters_log = add_agent(any_space, _MessagingTestAgent, "Webster")
    chattys_log = add_agent(any_space, _MessagingTestAgent, "Chatty")

    # Send the first message and wait for a response
    first_message = {
        'from': 'Webster',
        'to': 'Chatty',
        'action': {
            'name': 'say_with_say',
            'args': {
                'content': 'Hello, Chatty!'
            }
        }
    }
    any_space._route(first_message)
    assert_message_log(websters_log, [
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
    ])


def test_send_and_return(any_space):
    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, _MessagingTestAgent, "Chatty")

    first_message = {
        'meta': {
            "id": "123 whatever i feel like here"
        },
        'to': 'Chatty',
        'from': 'Webster',
        'action': {
            'name': 'say_with_return',
            'args': {
                'content': 'Hi Chatty!'
            }
        }
    }
    any_space._route(first_message)
    assert_message_log(websters_log, [{
        "meta": {
            "response_id": "123 whatever i feel like here",
        },
        "to": "Webster",
        "from": "Chatty",
        "action": {
            "name": "response",
            "args": {
                "value": ["Hello!"],
            }
        }
    }])


def test_send_and_error(any_space):
    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, ObservableAgent, "Chatty")

    # this message will result in an error
    any_space._route({
        'meta': {
            'id': '456 whatever i feel like here',
        },
        'to': 'Chatty',
        'from': 'Webster',
        'action': {
            'name': 'some non existent action',
            'args': {
                'content': 'Hi Chatty!'
            }
        }
    })

    assert_message_log(websters_log, [{
        "meta": {
            "response_id": "456 whatever i feel like here",
        },
        "to": "Webster",
        "from": "Chatty",
        "action": {
            "name": "response",
            "args": {
                "error": "\"some non existent action\" not found on \"Chatty\"",
            }
        }
    }])


@pytest.mark.skip
def test_request_and_return(any_space):
    raise NotImplementedError


@pytest.mark.skip
def test_request_and_error(any_space):
    raise NotImplementedError


class _SelfReceivedBroadcastAgent(ObservableAgent):
    @action
    def say(self, content: str):
        pass


def test_self_received_broadcast(any_space):
    websters_log = add_agent(any_space, ObservableAgent,
                             "Webster", receive_own_broadcasts=True)
    chattys_log = add_agent(any_space, _SelfReceivedBroadcastAgent, "Chatty")
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
    any_space._route(first_message)
    assert_message_log(websters_log, [first_message])
    assert_message_log(chattys_log, [first_message])


class _NonSelfReceivedBroadcastAgent(ObservableAgent):
    @action
    def say(self, content: str):
        pass


def test_non_self_received_broadcast(any_space):
    websters_log = add_agent(any_space, ObservableAgent, "Webster",
                             receive_own_broadcasts=False)
    chattys_log = add_agent(
        any_space, _NonSelfReceivedBroadcastAgent, "Chatty")

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
    any_space._route(first_message)
    assert_message_log(websters_log, [])
    assert_message_log(chattys_log, [first_message])


def test_meta(any_space):
    """
    Tests that the meta field is transmitted
    """

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, _MessagingTestAgent, "Chatty")

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
    any_space._route(first_message)
    assert_message_log(chattys_log, [first_message])


def test_send_undefined_action(any_space):
    """Tests sending an undefined action and receiving an error response"""

    # In this test we skip defining a say action on chatty in order to test the
    # error response

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, ObservableAgent, "Chatty")

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
                    "error": "\"say\" not found on \"Chatty\"",
                },
            }
        },
    ])
