import time
from agents.chatty_ai import ChattyAI
from agency.amqp_space import AMQPSpace

if __name__ == '__main__':

    space = AMQPSpace()

    # Add a simple HF chat agent to the space
    space.add(
        ChattyAI("Chatty",
                 model="EleutherAI/gpt-neo-125m"))

    # keep alive
    while True:
        time.sleep(1)
