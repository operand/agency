from agency.agent import (ACCESS_DENIED, ACCESS_REQUESTED, action)
from tests.helpers import ObservableAgent, add_agent, assert_message_log


# NOTE: Tests below define one or two agent classes before each test function


class _HelpActionAgent(ObservableAgent):
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


def test_help_action(any_space):
    """Tests defining help info, requesting it, receiving the response"""

    chattys_expected_response = {
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

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, _HelpActionAgent, "Chatty")

    # Send the first message and wait for a response
    first_message = {
        'to': '*',  # broadcast
        'from': 'Webster',
        'action': {
            'name': 'help',
            'args': {}
        }
    }
    any_space._route(first_message)
    assert_message_log(websters_log, [chattys_expected_response])
    assert_message_log(chattys_log, [first_message, chattys_expected_response])


class _HelpSpecificActionAgent(ObservableAgent):
    @action
    def action_i_will_request_help_on():
        pass

    @action
    def action_i_dont_care_about():
        pass


def test_help_specific_action(any_space):
    """Tests requesting help for a specific action"""

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, _HelpSpecificActionAgent, "Chatty")

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
    any_space.send_test_message(first_message)
    assert_message_log(websters_log, [
        {
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
    ])


class _ResponsesHaveOriginalMessageIdAgent(ObservableAgent):
    @action
    def say(self, content: str):
        return ["Hello!"]


def test_responses_have_original_message_id(any_space):
    """Tests that original_message_id is populated on responses and errors"""

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(
        any_space, _ResponsesHaveOriginalMessageIdAgent, "Chatty")

    # this message will result in a response with data
    any_space.send_test_message({
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


def test_errors_have_original_message_id(any_space):
    """Tests that original_message_id is populated on errors"""

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, ObservableAgent, "Chatty")

    # this message will result in an error
    any_space.send_test_message({
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
    any_space.send_test_message(first_message)
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
    any_space.send_test_message(first_message)
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
    """Tests sending a basic "say" message receiving a reply"""
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
    any_space.send_test_message(first_message)
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


class MetaAgent(ObservableAgent):
    @action
    def say(self, content: str):
        pass


def test_meta(any_space):
    """
    Tests that the meta field is transmitted
    """

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, MetaAgent, "Chatty")

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
    any_space.send_test_message(first_message)
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
    any_space.send_test_message(first_message)
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


class _SendUnpermittedActionAgent(ObservableAgent):
    @action(access_policy=ACCESS_DENIED)
    def say(self, content: str):
        pass


def test_send_unpermitted_action(any_space):
    """Tests sending an unpermitted action and receiving an error response"""

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, _SendUnpermittedActionAgent, "Chatty")

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
    any_space.send_test_message(first_message)
    assert_message_log(websters_log, [
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
    ])


class _SendRequestPermittedActionAgent(ObservableAgent):
    @action(access_policy=ACCESS_REQUESTED)
    def say(self, content: str):
        return "42"

    def request_permission(self, proposed_message: dict) -> bool:
        return True


def test_send_request_permitted_action(any_space):
    """Tests sending an action, granting permission, and returning response"""
    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(
        any_space, _SendRequestPermittedActionAgent, "Chatty")

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
    any_space.send_test_message(first_message)
    assert_message_log(websters_log, [
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
    ])


class _SendRequestReceivedActionAgent(ObservableAgent):
    @action(access_policy=ACCESS_REQUESTED)
    def say(self, content: str):
        return "42"

    def request_permission(self, proposed_message: dict) -> bool:
        return False


def test_send_request_rejected_action(any_space):
    """Tests sending an action, rejecting permission, and returning error"""

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, _SendRequestReceivedActionAgent, "Chatty")

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
    any_space.send_test_message(first_message)
    assert_message_log(websters_log, [
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
    ])
