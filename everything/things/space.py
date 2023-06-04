from dotenv import load_dotenv
from everything.channels.channel import Channel
from everything.things import util
from everything.things.schema import MessageSchema
import asyncio
import threading


load_dotenv()


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
    self.created = threading.Event() # set when the space is fully created
    self.destructing = threading.Event() # set when the space is being destroyed
    for channel in self.channels:
      channel.space = self

  def id(self) -> str:
    return self.__class__.__name__

  async def __start_channel(self, channel):
    while not self.destructing.is_set():
      await channel._process()
      await asyncio.sleep(0.01)

  async def __start_channels(self):
    # start and run all channels concurrently
    channel_processes = [
      asyncio.create_task(self.__start_channel(channel))
      for channel in self.channels + [self]
    ]
    await asyncio.gather(*channel_processes)

  def create(self):
    # start channels thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    future = asyncio.run_coroutine_threadsafe(self.__start_channels(), loop)
    thread = threading.Thread(target=loop.run_forever)
    thread.start()
    print("A small pop...")
    self.created.set()
    try:
      # wait for the future to complete
      future.result()
    finally:
      # stop the event loop
      loop.call_soon_threadsafe(loop.stop)
      thread.join()
      loop.close()

  def destroy(self):
    self.destructing.set()

  def _route(self, message: MessageSchema):
    """
    Enqueues the action on intended recipient(s)
    """
    recipients = []
    if 'to' in message and message['to'] is not None:
      # if receiver is specified send to only that channel
      recipients = [
        channel for channel in self.channels
        if channel.id() == message['to']
      ]
    else:
      # if it isn't broadcast to all _but_ the sender
      recipients = [
        channel for channel in self.channels
        if channel.id() != message['from']
      ]
    
    # send to all, setting the 'to' field to the recipient's id
    util.debug(f"Routing to {[recipient.id() for recipient in recipients]}", message)
    for recipient in recipients:
      recipient._receive({
        **message,
        'to': recipient.id(),
      })

  def _get_help__sync(self, action=None) -> list:
    """
    Returns an action list immediately without forwarding messages
    """
    help = [
      channel._get_help(action)
      for channel in [self] + self.channels
    ]
    return help
