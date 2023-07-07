from agency.space import AMQPSpace
from agents.host import Host
import time


if __name__ == '__main__':

    space = AMQPSpace()

    # Add a host agent to the space, exposing access to the host system. We run
    # this application in the foreground in order to respond to permission
    # requests on the terminal
    space.add(Host("Host"))

    print("pop!")

    # keep alive
    while True:
        time.sleep(1)
