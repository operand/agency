import os

from agents.host import Host
from agents.openai_function_agent import OpenAIFunctionAgent

from agency.spaces.multiprocess_space import MultiprocessSpace
from examples.demo.apps.gradio_app import GradioApp

if __name__ == "__main__":

    # Create the space instance
    space = MultiprocessSpace()

    # Add a host agent to the space, exposing access to the host system
    space.add(Host, "Host")

    # Add an OpenAI function API agent to the space
    space.add(OpenAIFunctionAgent,
              "FunctionAI",
              model="gpt-3.5-turbo-16k",
              openai_api_key=os.getenv("OPENAI_API_KEY"),
              # user_id determines the "user" role in the OpenAI chat API
              user_id="User")

    # Add a Gradio app and its user to the space
    space.add(GradioApp, "User")

    # Other agents to try (see the ./agents directory)

    # Add an OpenAI agent based on the completion API
    # space.add(OpenAICompletionAgent,
    #           "CompletionAI",
    #           model="text-davinci-003",
    #           openai_api_key=os.getenv("OPENAI_API_KEY"))

    # Add a simple HF chat agent to the space
    # space.add(ChattyAI,
    #           "Chatty",
    #           model="EleutherAI/gpt-neo-125m")
