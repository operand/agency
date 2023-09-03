from agency.agent import (ACCESS_DENIED, ACCESS_REQUESTED, action)
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
                "whatever": { "I": "want" },
            },
            "stuff": ["a", "b", "c"]
        }
    )
    def action_with_custom_help():
        """The docstring here is ignored"""


def test_help_action(any_space):
    """Tests defining help info, requesting it, receiving the response"""

    first_message = {
        'to': '*',  # broadcast
        'from': 'Webster',
        'action': {
            'name': 'help',
            'args': {}
        }
    }

    chattys_expected_response = {
        "to": "Webster",
        "from": "Chatty",
        "action": {
            "name": "response",
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
                            "whatever": { "I": "want" },
                        },
                        "stuff": ["a", "b", "c"]
                    }
                },
                "original_message": first_message,
            }
        }
    }

    websters_log = add_agent(any_space, ObservableAgent, "Webster")
    chattys_log = add_agent(any_space, _HelpActionAgent, "Chatty")

    # Send the first message and wait for a response
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
    any_space._route(first_message)
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
