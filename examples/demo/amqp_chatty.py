from agency.space import AMQPSpace
from agents.chatty_ai import ChattyAI
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

    # Add a simple HF chat agent to the space
    space.add(
        ChattyAI("Chatty",
                 model="EleutherAI/gpt-neo-125m"))

    print("snap!")

    # keep alive
    while True:
        time.sleep(1)
