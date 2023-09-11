import os
import signal
import sys

from agents.host import Host
from agents.openai_function_agent import OpenAIFunctionAgent
from app.react_app import ReactApp

from agency.spaces.multiprocess_space import MultiprocessSpace

def sigint_handler(signum, frame):
    print("SIGINT received, shutting down")
    sys.exit(0)

if __name__ == "__main__":

    # Signal handler
    signal.signal(signal.SIGINT, sigint_handler)

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

    app = ReactApp(
        space=space,
        port=int(os.getenv("WEB_APP_PORT")),
        demo_username=os.getenv("User")
    )
    app.start()
