import os
import sys
import time
from agency.spaces.amqp_space import AMQPSpace

sys.path.append("../demo")
from apps.gradio_app import demo, gradio_user
from agents.openai_function_agent import OpenAIFunctionAgent

if __name__ == "__main__":
    space = AMQPSpace()

    space.add(gradio_user)

    # Add an OpenAI function API agent to the space
    space.add(
        OpenAIFunctionAgent(
            "FunctionAI",
            model="gpt-3.5-turbo-16k",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            # user_id determines the "user" role in the OpenAI chat API
            user_id="User",
        )
    )

    demo.launch(server_port=int(os.getenv("WEB_APP_PORT")))
