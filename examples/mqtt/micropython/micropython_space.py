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
            for agent in self.agents:
                if message_data['to'] == '*' or message_data['to'] == agent.id():
                    agent._receive(message_data)

        self.mqtt_client = MQTTClient(*args, **kwargs)
        self.mqtt_client.set_callback(_on_message)
        self.mqtt_client.connect()
        # _thread.start_new_thread(self.loop_forever, ())

    def add(self, agent) -> None:
        self.agents.append(agent)
        agent._space = self
        agent.after_add()

    def remove(self, agent) -> None:
        agent.before_remove()
        agent._space = None
        self.agents.remove(agent)

    def _route(self, message) -> None:
        # todo message integrity check
        assert "to" in message
        assert "from" in message
        assert "action" in message
        # ...

        if message['to'] == '*':
            # broadcast
            routing_key = self.BROADCAST_KEY
        else:
            # point to point
            routing_key = message['to']

        self.__publish(routing_key, message)
        

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
