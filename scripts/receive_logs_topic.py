# #!/usr/bin/env python

"""
# https://www.rabbitmq.com/tutorials/tutorial-five-python.html
# https://github.com/rabbitmq/rabbitmq-tutorials/blob/main/python/receive_logs_topic.py

Usage:
-  python receive_logs_topic.py "#" :  To receive all the logs
-  python receive_logs_topic.py "kern.*" : To receive all logs from the facility "kern"
-  python receive_logs_topic.py "*.critical" : To hear only about "critical" logs
-  python receive_logs_topic.py "kern.*" "*.critical" :  Create multiple bindings
"""

import sys
import os
import time
import socket
import kombu


def main():
    connection = kombu.Connection(
        hostname="localhost",
        port=5672,
        userid="guest",
        password="guest",
        virtual_host="/",
    )

    with connection as conn:
        exchange = kombu.Exchange("agency", type="topic", durable=False)
        binding_keys = sys.argv[1:]
        if not binding_keys:
            sys.stderr.write("Usage: %s [binding_key]...\n" % sys.argv[0])
            sys.exit(1)

        queues = [
            kombu.Queue("logs_topic", exchange=exchange, routing_key=binding_key)
            for binding_key in binding_keys
        ]

        for queue in queues:
            queue(conn.channel()).declare()

        def callback(body, message):
            message.ack()
            print(" [x] %r:%r" % (message.delivery_info["routing_key"], body))

        with conn.Consumer(queues, callbacks=[callback]):
            print(" [*] Waiting for logs. To exit press CTRL+C")
            while True:
                time.sleep(0.01)
                conn.heartbeat_check()  # sends heartbeat if necessary
                try:
                    conn.drain_events(timeout=0.01)
                except socket.timeout:
                    pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
