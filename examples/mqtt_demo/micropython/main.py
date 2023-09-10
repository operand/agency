# connect wifi
import time
import network
from machine import Pin

from micropython_agent import UAgent, action
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
        help = {
            "set": {
                "description": "can set device state of Smart Home. device: [fan, light], state: [on, off]",
                "args": {
                    "device": {"type": "string"},
                    "state": {"type": "string"},
                },
            }
        }

        if action_name:
            return help.get(action_name)
        else:
            return help

    def after_add(self):
        self.send({
            "meta": {
                "response_id": "help_request",
            },
            "to": "*",
            "action": {
                "name": "[response]",
                "args": {
                    "value": self._help(),
                }
            }
        })

    @action
    def set(self, device: str, state: str):
        print(device, state)
        map_ = {"on": 1, "off": 0}
        if device == "fan":
            self.fan.value(map_[state])
        if device == "light":
            self.light.value(map_[state])
        return "ok"

    @action
    def say(self, content: str):
        pass

class RobotAgent(UAgent):
    def __init__(self, id: str) -> None:
        super().__init__(id)

    def _help(self, action_name: str = None) -> list:
        help = {
            "set": {
                "description": "Sends a message to this agent",
                "args": {
                    "content": {"type": "string"},
                },
            }
        }

        if action_name:
            return help.get(action_name)
        else:
            return help

    def after_add(self):
        self.send({
            "meta": {
                "response_id": "help_request",
            },
            "to": "*",
            "action": {
                "name": "[response]",
                "args": {
                    "value": self._help(),
                }
            }
        })

    @action
    def say(self, content: str):
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
