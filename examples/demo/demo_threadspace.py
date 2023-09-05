import os

from agents.host import Host
from agents.openai_function_agent import OpenAIFunctionAgent

from agency.spaces.thread_space import ThreadSpace
from examples.demo.apps.gradio_app import GradioApp


if __name__ == "__main__":

    # Create the space instance
    space = ThreadSpace()

    # Add a Host agent to the space, exposing access to the host system
    space.add(Host, "Host")

    # Add an OpenAI function API agent to the space
    space.add(OpenAIFunctionAgent,
              "FunctionAI",
              model="gpt-3.5-turbo-16k",
              openai_api_key=os.getenv("OPENAI_API_KEY"),
              # user_id determines the "user" role in the OpenAI chat API
              user_id="User")

    # GradioApp adds its own user to the space in its constructor
    demo = GradioApp(space).demo()
    demo.launch()

    # Other agents to try

    # Add an OpenAI agent based on the completion API
    # space.add(OpenAICompletionAgent,
    #           "CompletionAI",
    #           model="text-davinci-003",
    #           openai_api_key=os.getenv("OPENAI_API_KEY"))

    # Add a simple HF chat agent to the space
    # space.add(ChattyAI,
    #           "Chatty",
    #           model="EleutherAI/gpt-neo-125m")

    # if __name__ == '__main__':
    #     # Importing and launching the Gradio demo from this file allows us to use
    #     # the `gradio` command line for live reloading
    #     demo.launch()
