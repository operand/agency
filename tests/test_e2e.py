from tests.helpers import Webster, wait_for_messages
from agency.agent import (ACCESS_DENIED, ACCESS_REQUESTED, Agent, action)


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
    assert webster._message_log[1] == {  # chatty's response
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
