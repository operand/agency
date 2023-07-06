from agency.space import AMQPSpace
from agents.host import Host
from agents.openai_completion_agent import OpenAICompletionAgent
from agents.openai_function_agent import OpenAIFunctionAgent
from web_app import WebApp
import os
import time


if __name__ == '__main__':

    space = AMQPSpace()

    # Add a host agent to the space, exposing access to the host system. We run
    # this application in the foreground in order to respond to permission
    # requests on the terminal
    space.add(Host("Host"))

    print("pop!")

    # keep alive
    while True:
        time.sleep(1)
