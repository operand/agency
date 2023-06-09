from everything.things import util
from everything.things.operator import Operator
from everything.things.schema import MessageSchema
import threading


class Space(Operator):
  """
  A Space is itself an Operator and is responsible for:
  - starting itself and its member operators
  - routing all messages sent by its member operators
  """

  def __init__(self, id, operators):
    super().__init__(id=id)
    self.operators = operators
    for operator in self.operators:
      operator._space = self

    self.threads = []
    self.created = threading.Event()  # set when the space is fully created
    self.destructing = threading.Event()  # set when the space is being destroyed

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

  # TODO: cache and invalidate when operators are added/removed
  def __gather_ids(self):
    """
    Returns a list of all operator ids in this and child spaces
    """
    ids = []
    for _operator in self.operators:
      if isinstance(_operator, Space):
        ids.extend(_operator.__gather_ids())
      else:
        ids.append(_operator.id())
    ids.append(self.id())
    return ids

  def _route(self, message: MessageSchema):
    """
    Enqueues the action on intended recipient(s)
    """
    operator_ids = self.__gather_ids()
    util.debug(f"*[{self.id()}] operators:", operator_ids)

    recipients = []
    if 'to' in message and message['to'] not in [None]:
      # if 'to' is specified send to only that operator
      recipients = [
        operator
        for operator in self.operators + [self]
        if operator.id() == message['to']
      ]
    else:
      # if 'to' is not specified broadcast to all _but_ the sender
      recipients = [
        operator
        for operator in self.operators + [self]
        if operator.id() != message['from']
      ]

    util.debug(
      f"*[{self.id()}] Routing to {len(recipients)} recipients")
    if len(recipients) == 0:
      # no recipient operator id matched
      if hasattr(self, '_space'):
        # pass to the parent space for routing
        self._space._route(message)
      else:
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
