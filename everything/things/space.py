from everything.things import util
from everything.things.operator import Operator
from everything.things.schema import MessageSchema
import threading

from numpy import broadcast


class Space(Operator):
    """
    A Space is itself an Operator and is responsible for:
    - starting itself and its member operators
    - routing all messages sent to/from member operators
    """

    def __init__(self, id, operators):
        super().__init__(id=id)
        self.operators = operators
        for operator in self.operators:
            operator._space = self
        self.threads = []
        self.created = threading.Event()    # set when the space is fully created
        self.destructing = threading.Event()    # set when the space is being destroyed

    def create(self):
        """
        Starts the Space and all Operators"""
        for operator in self.operators + [self]:
            thread = threading.Thread(target=operator._run)
            self.threads.append(thread)
            thread.start()
        print("A small pop...")
        self.created.set()
        while not self.destructing.is_set():
            self.destructing.wait(0.1)

    def destroy(self):
        self.destructing.set()
        for operator in self.operators + [self]:
            operator._stop()
        for thread in self.threads:
            thread.join()

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
                    util.debug(
                        f"*[{self.id()}] routing down to:", operator.id())
                    operator._route(message)
                    return

        if len(recipients) == 0:
            # no recipient operator id matched
            if self._space is not None:
                # pass to the parent space for routing
                util.debug(f"*[{self.id()}] routing up to:", self._space.id())
                self._space._route(message)
            else:
                util.debug(
                    f"*[{self.id()}] no recipient for message:", message)
                exit(1)    # temporary
                # route an error message back to the original sender
                # TODO: protect against infinite loops here
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
            # send to recipients, setting the 'to' field to their id
            for recipient in recipients:
                util.debug(f"*[{self.id()}] receiving on:", recipient.id())
                recipient._receive({
                    **message,
                    'to': recipient.id(),
                })

    def _get_help__sync(self, action_name: str = None) -> list:
        """
        Returns an action list immediately without forwarding messages
        """
        help = [
            operator._get_help(action_name)
            for operator in [self] + self.operators
        ]
        return help
