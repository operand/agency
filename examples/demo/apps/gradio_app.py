import json
import re
import gradio as gr
from agency.agent import Agent, action
from agency.schema import Message


class GradioUser(Agent):
    """
    Represents the Gradio user as an Agent and contains methods for integrating
    with the Chatbot component
    """
    def __init__(self, id: str):
        super().__init__(id, receive_own_broadcasts=False)

    @action
    def say(self, content):
        # We don't do anything to render an incoming message here because the
        # get_chatbot_messages method will render the full message history
        pass

    def send_message(self, text):
        """
        Sends a message as this user
        """
        message = self.__parse_input_message(text)
        self.send(message)
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

        if message['from'] == self.id():
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

        Returns:
            Message: The parsed message for sending
        """
        text = text.strip()

        if not text.startswith("/"):
            # assume it's a broadcasted "say"
            return {
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

        agent_id, action_name, args_str = match.groups()

        if agent_id is None:
            raise ValueError("Agent ID must be provided. Example: '/MyAgent.say' or '/*.say'")

        args_pattern = r'(\w+):"([^"]*)"'
        args = dict(re.findall(args_pattern, args_str))

        return {
            "to": agent_id.strip('"'),
            "action": {
                "name": action_name,
                "args": args
            }
        }

    def demo(self):
        # The following adapted from: https://www.gradio.app/docs/chatbot#demos

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

        with gr.Blocks(css=css, title="Agency Demo") as demo:
            # Chatbot area
            chatbot = gr.Chatbot(
                self.get_chatbot_messages,
                show_label=False,
                elem_id="chatbot",
            )

            # Input area
            with gr.Row():
                txt = gr.Textbox(
                    show_label=False,
                    placeholder="Enter text and press enter",
                    container=False,
                )
                btn = gr.Button("Send", scale=0)

            # Callbacks
            txt.submit(self.send_message, [txt], [txt, chatbot])
            btn.click(self.send_message, [txt], [txt, chatbot])

            # Continously updates the chatbot. Runs only while client is connected.
            demo.load(
                self.get_chatbot_messages, None, [chatbot], every=1
            )

        # Queueing necessary for periodic events using `every`
        demo.queue()
        return demo
