import json
import textwrap

import openai
from agents.mixins.help_methods import HelpMethods
from agents.mixins.say_response_methods import SayResponseMethods

from agency.agent import _RESPONSE_ACTION_NAME, Agent, action


class OpenAIFunctionAgent(HelpMethods, SayResponseMethods, Agent):
    """
    An agent which uses OpenAI's function calling API
    """

    def __init__(self, id, model, openai_api_key, user_id):
        super().__init__(id, receive_own_broadcasts=False)
        self.__model = model
        self.__user_id = user_id
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
        your ability to solve any problems at hand.

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
            # ignore response messages
            if message['action']['name'] != _RESPONSE_ACTION_NAME:
                # "say" actions are converted to messages using the content arg
                if message['action']['name'] == "say":
                    # assistant
                    if message['from'] == self.id():
                        open_ai_messages.append({
                            "role": "assistant",
                            "content": message["action"]["args"]["content"],
                        })
                    # user
                    elif message['from'] == self.__user_id:
                        open_ai_messages.append({
                            "role": "user",
                            "content": message["action"]["args"]["content"],
                        })

                    # a "say" from anyone else is considered a function message
                    else:
                        open_ai_messages.append({
                            "role": "function",
                            "name": f"{'-'.join(message['from'].split('.'))}-{message['action']['name']}",
                            "content": message["action"]["args"]["content"],
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
                        "content": f"""{message['from']} called function "{message['action']['name']}" with args {message['action'].get('args', {})}""",
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
                "name": f"{agent_id}-{action_name}",
                "description": action_help.get("description", ""),
                "parameters": {
                    "type": "object",
                    "properties": action_help['args'],
                    "required": [
                        # We don't currently support a notion of required args
                        # so we make everything required
                        arg_name for arg_name in action_help['args'].keys()
                    ],
                }
            }
            for agent_id, actions in self._available_actions.items()
            for action_name, action_help in actions.items()
            if not (agent_id == self.__user_id and action_name == "say")
            # the openai chat api handles a chat message differently than a
            # function, so we don't list the user's "say" action as a function
        ]
        return functions

    @action
    def say(self, content: str) -> bool:
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
        message = {
            "to": self.__user_id,
            "action": {}
        }
        response_message = completion['choices'][0]['message']
        if 'function_call' in response_message:
            # extract receiver and action
            function_parts = response_message['function_call']['name'].split(
                '-')
            message['to'] = "-".join(function_parts[:-1])  # all but last
            message['action']['name'] = function_parts[-1]  # last
            # arguments comes as a string when it probably should be an object
            if isinstance(response_message['function_call']['arguments'], str):
                message['action']['args'] = json.loads(
                    response_message['function_call']['arguments'])
            else:
                message['action']['args'] = response_message['function_call']['arguments']
        else:
            message['action']['name'] = "say"
            message['action']['args'] = {
                "content": response_message['content'],
            }

        self.send(message)
