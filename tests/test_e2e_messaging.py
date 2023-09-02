from agency.agent import action
from tests.helpers import ObservableAgent, add_agent, assert_message_log

"""
send/response
send/error
request/response
request/error
"""


class _ResponsesHaveOriginalMessageIdAgent(ObservableAgent):
    @action
    def say(self, content: str):
        return ["Hello!"]


def test_send_and_response(any_space):
    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(
        any_space, _ResponsesHaveOriginalMessageIdAgent, "Chatty")

    # this message will result in a response with data
    any_space._route({
        'id': '123 whatever i feel like here',
        'to': 'Chatty',
        'from': 'Webster',
        'action': {
            'name': 'say',
            'args': {
                'content': 'Hi Chatty!'
            }
        }
    })

    assert_message_log(websters_log, [{
        "to": "Webster",
        "from": "Chatty",
        "action": {
            "name": "response",
            "args": {
                "data": ["Hello!"],
                "original_message_id": "123 whatever i feel like here",
            }
        }
    }])


def test_send_and_error(any_space):
    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, ObservableAgent, "Chatty")

    # this message will result in an error
    any_space._route({
        'id': '456 whatever i feel like here',
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
        "to": "Webster",
        "from": "Chatty",
        "action": {
            "name": "error",
            "args": {
                "error": "\"some non existent action\" not found on \"Chatty\"",
                "original_message_id": "456 whatever i feel like here",
            }
        }
    }])


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


class _SendAndReceiveAgentOne(ObservableAgent):
    @action
    def say(self, content: str):
        pass


class _SendAndReceiveAgentTwo(ObservableAgent):
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


def test_send_and_receive(any_space):
    """Tests sending a basic "say" message and receiving one back"""
    websters_log = add_agent(any_space, _SendAndReceiveAgentOne, "Webster")
    chattys_log = add_agent(any_space, _SendAndReceiveAgentTwo, "Chatty")

    # Send the first message and wait for a response
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


class _MetaAgent(ObservableAgent):
    @action
    def say(self, content: str):
        pass


def test_meta(any_space):
    """
    Tests that the meta field is transmitted
    """

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, _MetaAgent, "Chatty")

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
    ])
