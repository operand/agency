from agency.native_space import NativeSpace
from agents.host import Host
from agents.openai_function_agent import OpenAIFunctionAgent
from apps.gradio_app import demo, gradio_user
import os


# Create the space instance
space = NativeSpace()

# Add a host agent to the space, exposing access to the host system
space.add(Host("Host"))

# Add an OpenAI function API agent to the space
space.add(
    OpenAIFunctionAgent("FunctionAI",
                        model="gpt-3.5-turbo-16k",
                        openai_api_key=os.getenv("OPENAI_API_KEY"),
                        # user_id determines the "user" role in the OpenAI chat API
                        user_id="User"))


# Other agents to try

# Add an OpenAI agent based on the completion API
# space.add(
#     OpenAICompletionAgent("CompletionAI",
#                           model="text-davinci-003",
#                           openai_api_key=os.getenv("OPENAI_API_KEY")))

# Add a simple HF chat agent to the space
# space.add(
#     ChattyAI("Chatty",
#              model="EleutherAI/gpt-neo-125m"))


# Connect the Gradio app user to the space
space.add(gradio_user)


if __name__ == '__main__':
    # Importing and launching the Gradio demo from this file allows us to use
    # the `gradio` command line for live reloading
    demo.launch()
