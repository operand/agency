import os
import time

from agency.spaces.local_space import LocalSpace
from examples.demo.agents.host import Host
from examples.demo.agents.openai_function_agent import OpenAIFunctionAgent
from examples.demo.apps.gradio_app import GradioUser

if __name__ == "__main__":

    # Create the space instance
    with LocalSpace() as space:

        # Add a host agent to the space, exposing access to the host system
        space.add(Host, "Host")

        # Add an OpenAI function API agent to the space
        space.add(OpenAIFunctionAgent,
                  "FunctionAI",
                  model="gpt-3.5-turbo-16k",
                  openai_api_key=os.getenv("OPENAI_API_KEY"),
                  # user_id determines the "user" role in the OpenAI chat API
                  user_id="User")

        # Connect the Gradio app user to the space
        gradio_user: GradioUser = space.add_foreground(GradioUser, "User")

        # Launch the gradio app
        gradio_user.demo().launch(
            server_name="0.0.0.0",
            server_port=8080,
            prevent_thread_lock=True,
            quiet=True,
        )

        try:
            # block here until Ctrl-C
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
