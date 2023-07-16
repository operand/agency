import os
import time

from agents.openai_completion_agent import OpenAICompletionAgent
from agents.openai_function_agent import OpenAIFunctionAgent

from agency.amqp_space import AMQPSpace

if __name__ == '__main__':

    space = AMQPSpace()

    # Add an OpenAI function API agent to the space
    space.add(
        OpenAIFunctionAgent("FunctionAI",
                            model="gpt-3.5-turbo-16k",
                            openai_api_key=os.getenv("OPENAI_API_KEY"),
                            # user_id determines the "user" role in the OpenAI chat API
                            user_id="Dan"))

    # Add an OpenAI agent based on the completion API
    space.add(
        OpenAICompletionAgent("CompletionAI",
                              model="text-davinci-003",
                              openai_api_key=os.getenv("OPENAI_API_KEY")))

    while True:
        time.sleep(1)
