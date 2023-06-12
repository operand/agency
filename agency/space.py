from agency.agent import Agent
from agency.schema import MessageSchema


class Space(Agent):
    """
    A Space is itself an Agent and is responsible for:
    - starting/stopping itself and its member agents
    - routing all messages for its member agents
    """

    def __init__(self, id):
        """Creates and starts the Space"""
        super().__init__(id=id)
        self.agents = []

    def add(self, agent: Agent):
        """Adds and starts an agent to the space"""
        self.agents.append(agent)
        agent.space = self
        if self.running.is_set():
            agent.run()

    def run(self):
        """Runs the agent in a thread"""
        super().run()
        for agent in self.agents:
            agent.run()

    def _agent_ids(self, recursive: bool = True):
        """
        Returns a list of all agent ids in this space not including itself.
        If recursive is True (default) it includes agent ids in child spaces.
        """
        ids = []
        for _agent in self.agents:
            if recursive and isinstance(_agent, Space):
                ids.extend(_agent._agent_ids())
            else:
                ids.append(_agent.id())
        return ids

    def _route(self, message: MessageSchema):
        """
        Enqueues the action on intended recipient(s)
        """
        broadcast = False
        if 'to' not in message or message['to'] in [None, ""]:
            broadcast = True

        recipients = []
        for agent in self.agents:
            if broadcast and agent.id() != message['from']:
                # broadcast routing
                # NOTE this only broadcasts to direct member agents of the space
                recipients.append(agent)

            elif not broadcast:
                # point to point routing
                if agent.id() == message['to']:
                    recipients.append(agent)
                elif isinstance(agent, Space) and message['to'] in agent._agent_ids():
                    # pass to child space for routing and return
                    agent._route(message)
                    return

        if len(recipients) == 0:
            # no recipient agent id matched
            if self.space is not None:
                # pass to the parent space for routing
                self.space._route(message)
            else:
                # route an error back to the sender
                self._route({
                    'from': self.id(),
                    'to': message['from'],
                    'thoughts': 'An error occurred',
                    'action': 'error',
                    'args': {
                        'original_message': message,
                        'error': f"\"{message['to']}\" agent not found"
                    }
                })
        else:
            # enqueue message on recipients
            for recipient in recipients:
                recipient._receive(message)

    def _get_help__sync(self, action_name: str = None) -> list:
        """
        Returns an action list immediately without forwarding messages
        """
        help = [
            agent._get_help(action_name)
            for agent in [self] + self.agents
        ]
        return help
