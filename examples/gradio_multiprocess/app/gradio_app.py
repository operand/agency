import json
import multiprocessing
import re
from typing import List

import gradio as gr

from agency.agent import Agent, _QueueProtocol, action
from agency.schema import Message


class GradioUser(Agent):
    """
    Represents the Gradio app and its user as an Agent
    """

    def __init__(self,
                 id: str,
                 outbound_queue: _QueueProtocol,
                 _message_log: List[Message] = None,
                 ):
        super().__init__(id,
                         outbound_queue,
                         receive_own_broadcasts=False)
        self._message_log = _message_log

    @action
    def say(self, content):
        # We don't do anything to render here because the get_chatbot_messages
        # method will render the full message history based on the _message_log
        pass


class GradioApp():

    def __init__(self, space):
        self.space = space
        # Add the agent to the space. We pass a custom message log to the user
        # agent so that we can access it for rendering in the app
        self._agent_id = "User"
        self._message_log = multiprocessing.Manager().list()
        self.space.add(GradioUser, self._agent_id,
                       _message_log=self._message_log)

    def send_message(self, text):
        """
        Sends a message as this user
        """
        message = self.__parse_input_message(text)

        # The gradio app sends a message directly into the space as though it
        # were coming from the user. Because of this we also append to the
        # agent's _message_log, since we are bypassing that logic. This isn't
        # the greatest implementation but is a compromise since running gradio
        # in a subprocess is problematic.
        self._message_log.append(message)
        self.space._route(message)

        return "", self.get_chatbot_messages()

    def get_chatbot_messages(self):
        """
        Returns the full message history for the Chatbot component
        """
        return [
            self.__chatbot_message(message)
            for message in self._message_log
        ]

    def __chatbot_message(self, message):
        """
        Returns a single message as a tuple for the Chatbot component
        """
        text = f"**{message['from']}:** "
        if message['action']['name'] == 'say':
            text += f"{message['action']['args']['content']}"
        else:
            text += f"\n```javascript\n{json.dumps(message, indent=2)}\n```"

        if message['from'] == self._agent_id:
            return text, None
        else:
            return None, text

    def __parse_input_message(self, text) -> Message:
        """
        Parses input text into a message.

        If the text does not begin with "/", it is assumed to be a broadcasted
        "say" action, with the content argument set to the text.

        If the text begins with "/", it is assumed to be of the form:

            /agent_id.action_name arg1:val1 arg2:val2 ...

        Where agent_id and all argument names and values must be enclosed in
        quotes if they contain spaces. For example:

            /"agent with a space in the id".say content:"Hello, agent!"

        Args:
            text: The input text to parse

        Returns:
            Message: The parsed message for sending
        """
        text = text.strip()

        if not text.startswith("/"):
            # assume it's a broadcasted "say"
            return {
                "from": self._agent_id,
                "to": "*",
                "action": {
                    "name": "say",
                    "args": {
                        "content": text
                    }
                }
            }

        pattern = r'^/(?:((?:"[^"]+")|(?:[^.\s]+))\.)?(\w+)\s*(.*)$'
        match = re.match(pattern, text)

        if not match:
            raise ValueError("Invalid input format")

        to_agent_id, action_name, args_str = match.groups()

        if to_agent_id is None:
            raise ValueError(
                "Agent ID must be provided. Example: '/MyAgent.say' or '/*.say'")

        args_pattern = r'(\w+):"([^"]*)"'
        args = dict(re.findall(args_pattern, args_str))

        return {
            "from": self._agent_id,
            "to": to_agent_id.strip('"'),
            "action": {
                "name": action_name,
                "args": args
            }
        }

    def demo(self):
        """
        Returns the Gradio app.
        """

        # Custom css to:
        # - Expand text area to fill vertical space
        # - Remove orange border from the chat area that appears because of polling
        css = """
        .gradio-container {
            height: 100vh !important;
        }

        .gradio-container > .main,
        .gradio-container > .main > .wrap,
        .gradio-container > .main > .wrap > .contain,
        .gradio-container > .main > .wrap > .contain > div {
            height: 100% !important;
        }

        #chatbot {
            height: auto !important;
            flex-grow: 1 !important;
        }

        #chatbot > div.wrap {
            border: none !important;
        }
        """
        # Adapted from: https://www.gradio.app/docs/chatbot#demos
        with gr.Blocks(css=css, title="Agency Demo") as demo:
            # Chatbot area
            chatbot = gr.Chatbot(
                self.get_chatbot_messages,
                show_label=False,
                elem_id="chatbot")

            # Input area
            with gr.Row():
                txt = gr.Textbox(
                    show_label=False,
                    placeholder="Enter text and press enter",
                    container=False)
                btn = gr.Button("Send", scale=0)

            # Callbacks
            txt.submit(self.send_message, [txt], [txt, chatbot])
            btn.click(self.send_message, [txt], [txt, chatbot])

            # Continously updates the chatbot. Runs while client is connected.
            demo.load(self.get_chatbot_messages, None, [chatbot], every=1)

        # Queueing required for periodic events using `every`
        demo.queue()

        return demo
