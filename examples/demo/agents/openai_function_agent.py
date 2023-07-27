import json
import textwrap
import openai
from .mixins.help_methods import HelpMethods
from agency.agent import ACCESS_PERMITTED, Agent, access_policy


class OpenAIFunctionAgent(HelpMethods, Agent):
    """
    An agent which uses OpenAI's function calling API
    """

    def __init__(self, id, model, openai_api_key, **kwargs):
        super().__init__(id)
        self.__model = model
        self.__kwargs = kwargs
        openai.api_key = openai_api_key

    def __system_prompt(self):
        return textwrap.dedent(f"""
        You are "{self.id()}". You are a prototype of an "agent" system which
        can freely interact with its environment.

        Your creator has recently open-sourced your codebase intended to allow
        others to easily create their own AI integrated systems. He is
        demonstrating your abilities so that others can better understand agents
        like yourself and how you may integrate with the world.

        Your goal is to demonstrate your accurate understanding of the world and
        your ability to communicate with as needed to solve any problems at
        hand.

        The following is your current conversation. Respond appropriately.
        """)

    def __open_ai_messages(self):
        """
        Returns a list of messages converted from the message_log to be sent to
        OpenAI
        """
        # start with the system message
        open_ai_messages = [
            {"role": "system", "content": self.__system_prompt()}]

        # format and add the rest of the messages
        # NOTE: the chat api limits to only four predefined roles so we do our
        # best to translate to them here.
        for message in self._message_log:
            # "return" and "error" are converted by default to "say" so ignore
            if message['action'] not in ["return", "error"]:
                # "say" actions are converted to messages using the content arg
                if message['action'] == "say":
                    # assistant
                    if message['from'] == self.id():
                        open_ai_messages.append({
                            "role": "assistant",
                            "content": message["args"]["content"],
                        })
                    # user
                    elif message['from'] == self.__kwargs['user_id']:
                        open_ai_messages.append({
                            "role": "user",
                            "content": message["args"]["content"],
                        })

                    # a "say" from anyone else is considered a function message
                    else:
                        open_ai_messages.append({
                            "role": "function",
                            "name": f"{'-'.join(message['from'].split('.'))}-{message['action']}",
                            "content": message["args"]["content"],
                        })

                # all other actions are considered a function_call
                else:
                    # AFAICT from the documentation I've found, it does not
                    # appear that openai suggests including function_call
                    # messages (the responses from openai) in the messages list.
                    #
                    # I am going to add them here as a "system" message
                    # reporting the details of what the function call was. This
                    # is important information to infer from and it's currently
                    # not clear whether the language model has access to it
                    # during inference.
                    open_ai_messages.append({
                        "role": "system",
                        "content": f"""{message['from']} called function "{message['action']}" with args {message['args']}""",
                    })

        return open_ai_messages

    def __open_ai_functions(self):
        """
        Returns a list of functions converted from space._get_help__sync() to be
        sent to OpenAI as the functions arg
        """
        functions = [
            {
                # note that we send a fully qualified name for the action and
                # convert '.' to '-' since openai doesn't allow '.'
                "name": f"{action_help['to']}-{action_help['action']}",
                "description": action_help['thoughts'],
                "parameters": {
                    "type": "object",
                    "properties": {
                        arg_name: {
                            "type": self.__arg_type_to_openai_type(arg_type),
                            # this library doesn't support descriptions for
                            # args. maybe in the future. for now we skip it
                            "description": f"",
                        }
                        for arg_name, arg_type in action_help['args'].items()
                    },
                    "required": [
                        arg_name for arg_name, _ in action_help['args'].items()
                    ],
                }
            }
            for action_help in self._available_actions
            if not (action_help['to'] == self.__kwargs['user_id'] and action_help['action'] == "say")
            # the openai chat api handles "say" specially to the main user, by
            # treating it as a normal chat message
        ]
        return functions

    def __arg_type_to_openai_type(self, arg_type):
        """
        Converts an arg type to an openai type
        """
        if arg_type == "str":
            return "string"
        elif arg_type == "bool":
            return "boolean"
        elif arg_type == "list":
            return "array"
        elif arg_type == "dict":
            return "object"
        elif arg_type == "int":
            return "integer"
        else:
            raise ValueError(f"Unknown openai arg type for: {arg_type}")

    @access_policy(ACCESS_PERMITTED)
    def _action__say(self, content: str) -> bool:
        """
        Sends a message to this agent
        """
        completion = openai.ChatCompletion.create(
          model=self.__model,
          messages=self.__open_ai_messages(),
          functions=self.__open_ai_functions(),
          function_call="auto",
          # ... https://platform.openai.com/docs/api-reference/chat/create
        )

        # parse the output
        action = {
            # defaults
            "to": self.__kwargs['user_id'],
            # TODO we can add "thoughts" as an additional arg to each action but
            # for now this implementation will ignore it. the text completion
            # implementation does use the "thoughts" field correctly.
            "thoughts": "",
        }
        response_message = completion['choices'][0]['message']
        if 'function_call' in response_message:
            # extract receiver and action
            function_parts = response_message['function_call']['name'].split(
                '-')
            action['to'] = "-".join(function_parts[:-1])  # all but last
            action['action'] = function_parts[-1]  # last
            # arguments comes as a string when it probably should be an object
            if isinstance(response_message['function_call']['arguments'], str):
                action['args'] = json.loads(
                    response_message['function_call']['arguments'])
            else:
                action['args'] = response_message['function_call']['arguments']
        else:
            action['action'] = "say"
            action['args'] = {
                "content": response_message['content'],
            }

        self._send(action)
