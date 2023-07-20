import eventlet
eventlet.monkey_patch()

import os
import sys
import time
from agency.amqp_space import AMQPSpace

sys.path.append("../demo")
from web_app import WebApp
from agents.openai_function_agent import OpenAIFunctionAgent


class LightAMQPSpace(AMQPSpace):
    '''
    _check_queue_exists of AMQPSpace can't detect mqtt queue (but we can see it in the web management page)
    send message and do not check queue exists
    Used to send messages to MQTTAgent(eg: MicroPython Agent, SnapAgent)
    '''
    def _check_queue_exists(self, queue_name):
        return True

if __name__ == '__main__':

    space = LightAMQPSpace()

    # Create and start a web app to connect human users to the space.
    # As users connect they are added to the space as agents.
    web_app = WebApp(space,
                     port=os.getenv("WEB_APP_PORT"),
                     # NOTE We're hardcoding a single demo user for simplicity
                     demo_username="Dan")
    web_app.start()


    # Add an OpenAI function API agent to the space
    space.add(
        OpenAIFunctionAgent("FunctionAI",
                            model="gpt-3.5-turbo-16k",
                            openai_api_key=os.getenv("OPENAI_API_KEY"),
                            # user_id determines the "user" role in the OpenAI chat API
                            user_id="Dan"))
    

    # keep alive
    while True:
        time.sleep(1)
