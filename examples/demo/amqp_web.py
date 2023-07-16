import eventlet
eventlet.monkey_patch()

import os
import time
from web_app import WebApp
from agency.amqp_space import AMQPSpace


if __name__ == '__main__':

    space = AMQPSpace()

    # Create and start a web app to connect human users to the space.
    # As users connect they are added to the space as agents.
    web_app = WebApp(space,
                     port=os.getenv("WEB_APP_PORT"),
                     # NOTE We're hardcoding a single demo user for simplicity
                     demo_username="Dan")
    web_app.start()

    # keep alive
    while True:
        time.sleep(1)
