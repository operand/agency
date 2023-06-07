from everything.things.channel import Channel
from everything.things.schema import MessageSchema
import threading


class Space(Channel):
  """
  A Space is itself a channel and is responsible for:
  - starting and running itself and its member channels
  - routing all sent messages
  
  Space's could potentially be nested but this hasn't been tested
  """

  def __init__(self, channels):
    super().__init__(None)
    self.channels = channels
    self.threads = []
    self.created = threading.Event() # set when the space is fully created
    self.destructing = threading.Event()  # set when the space is being destroyed
    for channel in self.channels:
      channel.space = self

  def id(self) -> str:
    return self.__class__.__name__

  def create(self):
    """
    Starts the space and all channels"""
    for channel in self.channels + [self]:
      thread = threading.Thread(target=channel._run)
      self.threads.append(thread)
      thread.start()
    print("A small pop...")
    self.created.set()
    while not self.destructing.is_set():
      self.destructing.wait(0.1)

  def destroy(self):
    self.destructing.set()
    for channel in self.channels + [self]:
      channel._stop()
    for thread in self.threads:
      thread.join()

  def _route(self, message: MessageSchema):
    """
    Enqueues the action on intended recipient(s)
    """
    recipients = []
    if 'to' in message and message['to'] not in [None, self.id()]:
      # if receiver is specified send to only that channel
      # if the channel supports the action
      recipients = [
        channel for channel in self.channels
        if channel.id() == message['to']
        and channel._action_exists(message['action'])
      ]
    else:
      # if 'to' is not specified broadcast to all _but_ the sender
      # if the channel supports the action
      recipients = [
        channel for channel in self.channels
        if channel.id() != message['from']
        and channel._action_exists(message['action'])
      ]

    # no recipients means the action is not supported
    if len(recipients) == 0:
      # route an error message to the original sender
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
      channel._get_help(action_name)
      for channel in [self] + self.channels
    ]
    return help
