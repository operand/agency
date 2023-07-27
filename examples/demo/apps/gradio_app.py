import json
import gradio as gr
from agency import util
from agency.agent import ACCESS_PERMITTED, Agent, access_policy


# Adapted from: https://www.gradio.app/docs/chatbot#demos


class GradioUser(Agent):
    """
    Represents the Gradio user as an Agent and contains methods for integrating
    with the Chatbot component
    """

    @access_policy(ACCESS_PERMITTED)
    def _action__say(self, content):
        # We don't do anything to render here because the get_chatbot_messages
        # method will render the full message history
        pass

    def send_message(self, text):
        """
        Sends a message as this user
        """
        action = util.parse_slash_syntax_action(text)
        self._send(action)
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
        if message['action'] == 'say':
            text += f"{message['args']['content']}"
        else:
            text += f"\n```\n{json.dumps(message, indent=2)}\n```"

        if message['from'] == self.id():
            return text, None
        else:
            return None, text


gradio_user = GradioUser("User")

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

with gr.Blocks(css=css) as demo:
    # Chatbot area
    chatbot = gr.Chatbot(
        gradio_user.get_chatbot_messages,
        label="Agency Demo",
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
    txt.submit(gradio_user.send_message, [txt], [txt, chatbot])
    btn.click(gradio_user.send_message, [txt], [txt, chatbot])

    # Continously updates the chatbot. Runs only while client is connected.
    demo.load(
        gradio_user.get_chatbot_messages, None, [chatbot], every=1
    )

# Queueing necessary for periodic events using `every`
demo.queue()
