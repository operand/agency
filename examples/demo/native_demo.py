import eventlet
eventlet.monkey_patch()

import os
import time

from agents.chatty_ai import ChattyAI
from agents.host import Host
from agents.openai_completion_agent import OpenAICompletionAgent
from agents.openai_function_agent import OpenAIFunctionAgent
from web_app import WebApp

from agency.native_space import NativeSpace


if __name__ == '__main__':

    # Create a space
    space = NativeSpace()

    # Add a host agent to the space, exposing access to the host system
    space.add(Host("Host"))

    # Add a simple HF based chat agent to the space
    space.add(
        ChattyAI("Chatty",
                 model="EleutherAI/gpt-neo-125m"))

    # Add an OpenAI function API agent to the space
    space.add(
        OpenAIFunctionAgent("FunctionAI",
                            model="gpt-3.5-turbo-16k",
                            openai_api_key=os.getenv("OPENAI_API_KEY"),
                            # user_id determines the "user" role in the OpenAI chat API
                            user_id="Dan"))

    # Add another OpenAI agent based on the completion API
    space.add(
        OpenAICompletionAgent("CompletionAI",
                              model="text-davinci-003",
                              openai_api_key=os.getenv("OPENAI_API_KEY")))

    # Create and start a web app to connect human users to the space.
    # As users connect they are added to the space as agents.
    web_app = WebApp(space,
                     port=os.getenv("WEB_APP_PORT"),
                     # NOTE We're hardcoding a single demo user for simplicity
                     demo_username="Dan")
    web_app.start()

    print("pop!")

    # keep alive
    while True:
        time.sleep(1)
