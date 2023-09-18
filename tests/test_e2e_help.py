from agency.agent import Agent, action
from agency.space import Space
from agency.spaces.local_space import LocalSpace
from tests.helpers import assert_message_log


class _HelpActionAgent(Agent):
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
                "whatever": {"I": "want"},
            },
            "stuff": ["a", "b", "c"]
        }
    )
    def action_with_custom_help():
        """The docstring here is ignored"""


def test_help_action(any_space: Space):
    """Tests defining help info, requesting it, receiving the response"""

    first_message = {
        "meta": {"id": "123"},
        "from": "Sender",
        "to": "*",  # broadcast
        "action": {
            "name": "help",
        }
    }

    receivers_expected_response = {
        "meta": {"parent_id": "123"},
        "from": "Receiver",
        "to": "Sender",
        "action": {
            "name": "[response]",
            "args": {
                "value": {
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
                            "whatever": {"I": "want"},
                        },
                        "stuff": ["a", "b", "c"]
                    }
                },
            }
        }
    }

    sender = any_space.add_foreground(
        Agent, "Sender", receive_own_broadcasts=False)
    receiver = any_space.add_foreground(_HelpActionAgent, "Receiver")

    # Send the first message and wait for a response
    sender.send(first_message)
    assert_message_log(sender._message_log, [
        first_message, receivers_expected_response])
    assert_message_log(receiver._message_log, [
        first_message, receivers_expected_response])


class _HelpSpecificActionAgent(Agent):
    @action
    def action_i_will_request_help_on():
        pass

    @action
    def action_i_dont_care_about():
        pass


def test_help_specific_action(any_space: Space):
    """Tests requesting help for a specific action"""

    sender = any_space.add_foreground(Agent, "Sender", receive_own_broadcasts=False)
    any_space.add(_HelpSpecificActionAgent, "Receiver")

    first_message = {
        "meta": {
            "id": "123"
        },
        "to": "*",  # broadcast
        "from": "Sender",
        "action": {
            "name": "help",
            "args": {
                "action_name": "action_i_will_request_help_on"
            }
        }
    }
    sender.send(first_message)
    assert_message_log(sender._message_log, [
        first_message,
        {
            "meta": {
                "parent_id": "123"
            },
            "to": "Sender",
            "from": "Receiver",
            "action": {
                "name": "[response]",
                "args": {
                    "value": {
                        "action_i_will_request_help_on": {
                            "args": {},
                        },
                    },
                }
            }
        }
    ])
