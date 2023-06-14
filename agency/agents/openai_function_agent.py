from urllib import response
from agency import util
from agency.agent import ACCESS_PERMITTED, access_policy
from agency.agent import Agent
import openai
import textwrap


class OpenAIFunctionAgent(Agent):
    """
    An agent which uses OpenAI's function_call API for inference
    """

    def __init__(self, id, model, openai_api_key, **kwargs):
        super().__init__(id)
        self.__model = model
        self.__kwargs = kwargs
        openai.api_key = openai_api_key

    def __system_prompt(self):
        return textwrap.dedent(f"""
        You are "Demo". You are a prototype of an "agent" system which can
        freely interact with its environment.

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
        util.debug(f"* getting openai messages...")
        # start with the system message
        open_ai_messages = [{ "role": "system", "content": self.__system_prompt() }]

        # format and add the rest of the messages
        # NOTE: openai unfortunately limits us to four predefined chat roles so
        # we convert to them here. predefined roles aren't the right abstraction
        # IMHO but this is one way to handle it if we must.
        for message in self._message_log:
            # "say" actions are converted to messages using the content arg
            if message['action'] == "say":
                # assistant
                if message["from"] == self.id():
                    open_ai_messages.append({
                        "role": "assistant",
                        "content": message["args"]["content"],
                    })
                # user
                elif message["from"] == self.__kwargs['user_id']:
                    open_ai_messages.append({
                        "role": "user",
                        "content": message["args"]["content"],
                    })

                # a "say" from anyone else is considered a function message
                # NOTE this highlights one of the problems with predefined
                else:
                    open_ai_messages.append({
                        "role": "function",
                        "content": message["args"]["content"],
                    })

            # all other actions are considered a function_call
            else:
                # NOTE Strangely it does not appear that openai suggests
                # including function_call messages in the messages list. See:
                # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_call_functions_with_chat_models.ipynb
                #
                # I'm not sure why. Instead, I am going to add it here as a
                # "system" message reporting the details of what the function
                # call was. This is important information to infer from and it's
                # currently not clear from their documentation whether the
                # language model has access to it during inference. What if it
                # makes a mistake? It should see the function call details to
                # help it learn. And since this library also allows others to
                # call functions, it's important to be able to see what they are
                # calling as well.
                open_ai_messages.append({
                    "role": "system",
                    "content": f"""{message["from"]} called function "{message["action"]}" with args {message["args"]} and thoughts {message["thoughts"]}""",
                })

        util.debug(f"* openai messages:", open_ai_messages)

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
                "name": f"{action_help['to']}.{action_help['action']}".replace('.', '-'),
                "description": action_help['thoughts'],
                "parameters": {
                    "type": "object",
                    "properties": {
                        arg_name: {
                            "type": self.__arg_type_to_openai_type(arg_type),
                            # this library doesn't support descriptions for
                            # args. maybe in the future. for now:
                            "description": f"arg {arg_name} of type {arg_type}",
                        }
                        for arg_name, arg_type in action_help['args'].items()
                    },
                    "required": [
                        # i know.. we're looping twice. don't judge me.
                        arg_name for arg_name, _ in action_help['args'].items()
                    ],
                }
            }
            for action_help in self.space._get_help__sync()
            if action_help['action'] != "say"
            # the openai api handles "say" specially
        ]
        return functions

    def __arg_type_to_openai_type(self, arg_type):
        """
        Converts an arg type to an openai type
        """
        if arg_type == "str":
            return "string"
        elif arg_type == "number":
            return "number"
        elif arg_type == "bool":
            return "boolean"
        else:
            raise ValueError(f"Unknown openai arg type for: {arg_type}")

    @access_policy(ACCESS_PERMITTED)
    def _action__say(self, content: str) -> bool:
        """
        Sends a message to the openai chatcompletion api, translates the
        response, and sends the resulting action
        """
        completion = openai.ChatCompletion.create(
          model=self.__model,
          messages=self.__open_ai_messages(),
          functions=self.__open_ai_functions(),
          function_call="auto",
          # ... https://platform.openai.com/docs/api-reference/chat/create
        )
        util.debug(f"* openai response: {completion}")

        # parse the output
        action = {
            # defaults
            "to": self.__kwargs['user_id'],
            "thoughts": "",
        }
        response_message = completion['choices'][0]['message']
        if 'function_call' in response_message:
            # extract receiver and action
            function_parts = response_message['function_call']['name'].split('-')
            action['to'] = function_parts[:-1] # all but last
            action['action'] = function_parts[-1] # last
            action['action'] = action['action'].replace('-', '.') # convert back to '.'
            action['args'] = response_message['function_call']['arguments']
        else:
            action['action'] = "say"
            action['args'] = {
                "content": response_message['content'],
            }

        util.debug(f"* sending action:", action)

        self._send(action)
