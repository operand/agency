from agency.space import AMQPSpace
from web_app import WebApp
import os
import pika
import time


if __name__ == '__main__':

    # NOTE The following connection parameters are hardcoded to use a heartbeat
    # of 0. This is to workaround a bug that is currently being worked on. See:
    # https://github.com/operand/agency/issues/60
    space = AMQPSpace(
        pika_connection_params=pika.ConnectionParameters(
            heartbeat=0,
            host=os.environ.get('AMQP_HOST', 'localhost'),
            port=os.environ.get('AMQP_PORT', 5672),
            virtual_host=os.environ.get('AMQP_VHOST', '/'),
            credentials=pika.PlainCredentials(
                os.environ.get('AMQP_USERNAME', 'guest'),
                os.environ.get('AMQP_PASSWORD', 'guest'),
            ),
        )
    )

    # Create and start a web app to connect human users to the space.
    # As users connect they are added to the space as agents.
    web_app = WebApp(space,
                     port=os.getenv("WEB_APP_PORT"),
                     # NOTE We're hardcoding a single demo user for simplicity
                     demo_username="Dan")
    web_app.start()

    print("pop!")

    # keep alive
    while True:
        time.sleep(1)
