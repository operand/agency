from everything.things import util
from everything.things.operator import Operator
from everything.things.schema import MessageSchema


class Space(Operator):
    """
    A Space is itself an Operator and is responsible for:
    - starting/stopping itself and its member operators
    - routing all messages for its member operators
    """

    def __init__(self, id):
        """Creates and starts the Space"""
        super().__init__(id=id)
        self.operators = []

    def add(self, operator: Operator):
        """Adds and starts an operator to the space"""
        self.operators.append(operator)
        operator.space = self
        if self.running.is_set():
            operator.run()

    def run(self):
        """Runs the operator in a thread"""
        super().run()
        for operator in self.operators:
            operator.run()

    def _operator_ids(self, recursive: bool = True):
        """
        Returns a list of all operator ids in this space not including itself.
        If recursive is True (default) it includes operator ids in child spaces.
        """
        ids = []
        for _operator in self.operators:
            if recursive and isinstance(_operator, Space):
                ids.extend(_operator._operator_ids())
            else:
                ids.append(_operator.id())
        return ids

    def _route(self, message: MessageSchema):
        """
        Enqueues the action on intended recipient(s)
        """
        broadcast = False
        if 'to' not in message or message['to'] in [None, ""]:
            broadcast = True

        recipients = []
        for operator in self.operators:
            if broadcast and operator.id() != message['from']:
                # broadcast routing
                # NOTE this only broadcasts to direct member operators of the space
                recipients.append(operator)

            elif not broadcast:
                # point to point routing
                if operator.id() == message['to']:
                    recipients.append(operator)
                elif isinstance(operator, Space) and message['to'] in operator._operator_ids():
                    # pass to child space for routing and return
                    operator._route(message)
                    return

        if len(recipients) == 0:
            # no recipient operator id matched
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
                        'error': f"\"{message['to']}\" operator not found"
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
            operator._get_help(action_name)
            for operator in [self] + self.operators
        ]
        return help
