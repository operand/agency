# connect wifi
import time
import network
from machine import Pin

from micropython_agent import UAgent, access_policy, ACCESS_PERMITTED
from micropython_space import UMQTTSpace

# configure wifi
network_name = ""
network_password = ""

# configure MQTT
mqtt_broker_url = ""
mqtt_client_id = "umqtt_client"
mqtt_username = "guest"
mqtt_password = "guest"


class SmartHomeAgent(UAgent):
    def __init__(self, id: str) -> None:
        self.fan = Pin(16, Pin.OUT)
        self.light = Pin(22, Pin.OUT)
        super().__init__(id)

    def _help(self, action_name: str = None) -> list:
        help = [
            {
                "to": self.id(),
                "thoughts": "can set device state of Smart Home. device: [fan, light], state: [on, off]",
                "action": "set",
                "args": {
                    "device": "str",
                    "state": "str",
                },
            },
        ]

        if action_name:
            return [item for item in help if item["action"] == action_name]
        else:
            return help

    def _after_add(self):
        self._send(
            {
                "thoughts": "Here is a list of actions you can take on me.",
                "action": "return",
                "args": {
                    "original_message": {
                        "action": "help",
                    },
                    "return_value": self._help(),
                },
            }
        )

    @access_policy(ACCESS_PERMITTED)
    def _action__set(self, device: str, state: str):
        print(device, state)
        map_ = {"on": 1, "off": 0}
        if device == "fan":
            self.fan.value(map_[state])
        if device == "light":
            self.light.value(map_[state])
        return "ok"


class RobotAgent(UAgent):
    def __init__(self, id: str) -> None:
        super().__init__(id)

    def _help(self, action_name: str = None) -> list:
        help = [
            {
                "to": self.id(),
                "thoughts": "Sends a message to this agent",
                "action": "say",
                "args": {
                    "content": "str",
                },
            },
        ]

        if action_name:
            return [item for item in help if item["action"] == action_name]
        else:
            return help

    def _after_add(self):
        self._send(
            {
                "thoughts": "Here is a list of actions you can take on me.",
                "action": "return",
                "args": {
                    "original_message": {
                        "action": "help",
                    },
                    "return_value": self._help(),
                },
            }
        )

    @access_policy(ACCESS_PERMITTED)
    def _action__say(self, content: str):
        print(content)


# connect wifi
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect(network_name, network_password)
while not sta_if.isconnected():
    time.sleep(0.1)

# connect MQTT broker
space = UMQTTSpace(
    mqtt_client_id, mqtt_broker_url, user=mqtt_username, password=mqtt_password
)

agent = SmartHomeAgent("SmartHome")
agent2 = RobotAgent("Robot")

space.add(agent)
space.add(agent2)

space.start()
