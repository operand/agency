from everything.things.operator import Operator
from everything.things.schema import MessageSchema
import threading


class Space(Operator):
  """
  A Space is itself an operator and is responsible for:
  - starting itself and its member operators
  - routing all sent messages
  """

  def __init__(self, id, operators):
    super().__init__(id=id)
    self.operators = operators
    for operator in self.operators:
      operator.space = self
    self.threads = []
    self.created = threading.Event()  # set when the space is fully created
    self.destructing = threading.Event()  # set when the space is being destroyed

  def id(self) -> str:
    return self.__class__.__name__

  def create(self):
    """
    Starts the Space and all operators"""
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

  def _route(self, message: MessageSchema):
    """
    Enqueues the action on intended recipient(s)
    """
    recipients = []
    if 'to' in message and message['to'] not in [None, self.id()]:
      # if receiver is specified send to only that operator
      # if the operator supports the action
      recipients = [
        operator
        for operator in self.operators
        if operator.id() == message['to']
        and operator._action_exists(message['action'])
      ]
    else:
      # if 'to' is not specified broadcast to all _but_ the sender
      # if the operator supports the action
      recipients = [
        operator
        for operator in self.operators
        if operator.id() != message['from']
        and operator._action_exists(message['action'])
      ]

    # no recipients means the action is not supported
    if len(recipients) == 0:
      # route an error message back to the original sender
      # TODO: protect against infinite loops here
      self._route({
        'from': self.id(),
        'to': message['from'],
        'thoughts': 'An error occurred',
        'action': 'error',
        'args': {
          'original_message': message,
          'error': f"\"{message['action']}\" not found"
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
