import json
from umqtt.simple import MQTTClient # https://github.com/micropython/micropython-lib/tree/master/micropython/umqtt.simple, install from Thonny


class UMQTTSpace:
    """
    A Space that uses MQTT (RabbitMQ MQTT Plugin) for message delivery
    """

    BROADCAST_KEY = "__broadcast__"

    def __init__(self, *args, **kwargs):
        self.agents = []

        def _on_message(topic, msg):
            body = msg
            message_data = json.loads(json.loads(body))
            broadcast = "to" not in message_data or message_data["to"] in [None, ""]
            for agent in self.agents:
                if (
                    broadcast
                    and message_data["from"] != agent.id()
                    or not broadcast
                    and message_data["to"] == agent.id()
                ):
                    agent._receive(message_data)

        self.mqtt_client = MQTTClient(*args, **kwargs)
        self.mqtt_client.set_callback(_on_message)
        self.mqtt_client.connect()
        # _thread.start_new_thread(self.loop_forever, ())

    def add(self, agent) -> None:
        self.agents.append(agent)
        agent._space = self
        agent._after_add()

    def remove(self, agent) -> None:
        agent._before_remove()
        agent._space = None
        self.agents.remove(agent)

    def _route(self, sender, action: dict) -> dict:
        action["from"] = sender.id()
        message = action
        if "to" in message and message["to"] not in [None, ""]:
            # point to point
            routing_key = message["to"]
        else:
            # broadcast
            routing_key = self.BROADCAST_KEY
        sender._message_log.append(message)

        if routing_key == self.BROADCAST_KEY or routing_key:
            self.__publish(routing_key, message)
        else:
            if routing_key == sender.id():
                # if the routing key equals the sender id, we have a problem.
                # the sender's own queue doesn't exist so we can't route an
                # error back. raise an exception to prevent an infinite loop.
                raise Exception("Cannot route error. Missing sender queue.")
            else:
                # send an error back
                error_message = {
                    "from": sender.id(),
                    "to": sender.id(),
                    "thoughts": "An error occurred",
                    "action": "error",
                    "args": {
                        "original_message": message,
                        "error": f"\"{message['to']}\" not found",
                    },
                }
                self.__publish(sender.id(), error_message)

    def __publish(self, routing_key: str, message: dict):
        self.mqtt_client.publish(routing_key, json.dumps(message))

    def start(self):
        for agent in self.agents:
            self.mqtt_client.subscribe(agent.id())
        self.mqtt_client.subscribe(self.BROADCAST_KEY)

        print("wait for message...")
        try:
            while True:
                self.mqtt_client.wait_msg()
        finally:
            self.mqtt_client.disconnect()
