# #!/usr/bin/env python

"""
# https://www.rabbitmq.com/tutorials/tutorial-five-python.html
# https://github.com/rabbitmq/rabbitmq-tutorials/blob/main/python/receive_logs_topic.py

Usage:
-  python receive_logs_topic.py :  To receive all the logs
-  python receive_logs_topic.py --topic "#" :  To receive all the logs
-  python receive_logs_topic.py --topic "kern.*" : To receive all logs from the facility "kern"
-  python receive_logs_topic.py --topic "*.critical" : To hear only about "critical" logs
"""

import sys
import os
import time
import argparse

from agency.agent import Agent
from agency.amqp_space import AMQPSpace

class Watcher(Agent):
    def _receive(self, message: dict):
        print(message)

def main(topic):
    space = AMQPSpace()
    agent = Watcher("#")
    space.add(agent, receive_broadcast=False) # receive_broadcast=False: to avoid getting __broadcast__ messages twice

    while True:
        time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Message Watcher.")
    parser.add_argument("--topic", default="#", help="Subscribe to the topic messages.")
    args = parser.parse_args()

    try:
        main(args.topic)
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
