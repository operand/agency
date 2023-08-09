import os
from agency.spaces.amqp_space import AMQPSpace
from agents.host import Host
from agents.openai_function_agent import OpenAIFunctionAgent
from apps.gradio_app import demo, gradio_user


# Create the space instance
space = AMQPSpace()

# Add a host agent to the space, exposing access to the host system
space.add(Host("Host"))

# Add an OpenAI function API agent to the space
space.add(
    OpenAIFunctionAgent("FunctionAI",
                        model="gpt-3.5-turbo-16k",
                        openai_api_key=os.getenv("OPENAI_API_KEY"),
                        # user_id determines the "user" role in the OpenAI chat API
                        user_id="User"))

# Connect the Gradio app user to the space
space.add(gradio_user)


if __name__ == '__main__':
    # Importing and launching the Gradio demo from this file allows us to use
    # the `gradio` command line for live reloading
    demo.launch()
