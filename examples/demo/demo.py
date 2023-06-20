import os
import time
from agency.agents.chattyai import ChattyAI
from agency.agents.host import Host
from agency.agents.openai_completion_agent import OpenAICompletionAgent
from agency.agents.openai_function_agent import OpenAIFunctionAgent
from agency.space import Space
from agency.spaces.web_app import WebApp


if __name__ == '__main__':

    space = Space("DemoSpace")

    space.add(
        ChattyAI("Chatty",
            model="EleutherAI/gpt-neo-125m"))

    space.add(
        WebApp("WebApp",
            demo_user_id="Dan", # hardcoded for simplicity
            port='8080'))

    space.add(
        Host("Host"))

    space.add(
        OpenAIFunctionAgent("FunctionAI",
            model="gpt-3.5-turbo-16k",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            # user_id determines the "user" role in the OpenAI chat
            user_id="Dan.WebApp.DemoSpace"))

    space.add(
        OpenAICompletionAgent("CompletionAI",
            model="text-davinci-003",
            openai_api_key=os.getenv("OPENAI_API_KEY")))

    space.run()

    print("pop!")

    # keep alive
    while True:
        time.sleep(1)
