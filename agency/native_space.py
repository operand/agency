import queue
import threading
import time
from typing import List

from agency import util
from agency.agent import Agent
from agency.schema import MessageSchema
from agency.space import Space


class NativeSpace(Space):
    """
    A Space implementation that uses Python's built-in queue module.
    Suitable for single-process applications and testing.
    """

    def __init__(self):
        self.agents: List[Agent] = []

    def add(self, agent: Agent):
        agent._queue = queue.Queue()
        self.agents.append(agent)

        def _consume_messages():
            agent._space = self
            agent._thread_started.set()

            while not agent._thread_stopping.is_set():
                try:
                    message_dict = agent._queue.get(block=False)
                    message = MessageSchema(
                        **message_dict).dict(by_alias=True)  # validate
                    if 'to' not in message or message['to'] in [None, ""] or message['to'] == agent.id():
                        agent._receive(message)
                except queue.Empty:
                    pass
                time.sleep(0.01)
            agent._thread_stopped.set()

        threading.Thread(target=_consume_messages).start()
        agent._thread_started.wait()
        agent._after_add()

    def remove(self, agent: Agent):
        agent._before_remove()
        agent._thread_stopping.set()
        agent._thread_stopped.wait()
        agent._space = None
        self.agents.remove(agent)

    def _route(self, sender: Agent, action: dict) -> None:
        # Define and validate message
        message = MessageSchema(**{
          **action,
          "from": sender.id(),
        }).dict(by_alias=True)

        broadcast = False
        if 'to' not in message or message['to'] in [None, ""]:
            broadcast = True

        recipients = []
        for agent in self.agents:
            if broadcast and message['from'] != agent.id() or not broadcast and message['to'] == agent.id():
                recipients.append(agent)

        sender._message_log.append(message)
        if not broadcast and len(recipients) == 0:
            # send an error back
            error_message = MessageSchema(**{
                "from": sender.id(),
                "to": sender.id(),
                "thoughts": "An error occurred",
                "action": 'error',
                "args": {
                    'original_message': message,
                    'error': f"\"{message['to']}\" not found",
                }
            }).dict(by_alias=True)
            sender._queue.put(error_message)
        else:
            # enqueue message for recipients
            for recipient in recipients:
                recipient._queue.put(message)
