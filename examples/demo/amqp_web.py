from agency.space import AMQPSpace
from agents.host import Host
from agents.openai_completion_agent import OpenAICompletionAgent
from agents.openai_function_agent import OpenAIFunctionAgent
from web_app import WebApp
import os
import time


if __name__ == '__main__':

    space = AMQPSpace()

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
