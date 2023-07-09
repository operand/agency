import os
import time
import pika
from agents.chatty_ai import ChattyAI
from agency.space import AMQPSpace


if __name__ == '__main__':

    space = AMQPSpace(
        pika_connection_params=pika.ConnectionParameters(
            heartbeat=3,
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
