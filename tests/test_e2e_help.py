from agency.agent import action
from tests.helpers import ObservableAgent, add_agent, assert_message_log


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
                "whatever": {"I": "want"},
            },
            "stuff": ["a", "b", "c"]
        }
    )
    def action_with_custom_help():
        """The docstring here is ignored"""


def test_help_action(any_space):
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

    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, _HelpActionAgent, "Receiver")

    # Send the first message and wait for a response
    any_space._route(first_message)
    assert_message_log(
        senders_log, [receivers_expected_response])
    assert_message_log(
        receivers_log, [first_message, receivers_expected_response])


class _HelpSpecificActionAgent(ObservableAgent):
    @action
    def action_i_will_request_help_on():
        pass

    @action
    def action_i_dont_care_about():
        pass


def test_help_specific_action(any_space):
    """Tests requesting help for a specific action"""

    senders_log = add_agent(any_space, ObservableAgent, "Sender")
    receivers_log = add_agent(any_space, _HelpSpecificActionAgent, "Receiver")

    # Send the first message and wait for a response
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
    any_space._route(first_message)
    assert_message_log(senders_log, [
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
