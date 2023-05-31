from dotenv import load_dotenv
from everything.channels.channel import Channel
import asyncio
import threading


load_dotenv()


class Space(Channel):
  """
  A Space is itself a channel and is responsible for:
  - starting and running itself and its member channels
  - routing all sent messages
  
  Space's could eventually be nested (but this hasn't been tested yet)
  """

  def __init__(self, channels):
    super().__init__(None)
    self.channels = channels
    for channel in self.channels:
      channel.space = self

  def id(self):
    return self.__class__.__name__

  async def __start_channel(self, channel):
    self.running = True
    while self.running:
      await channel._process()
      await asyncio.sleep(1)

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
    try:
      # wait for the future to complete
      future.result()
    finally:
      # stop the event loop
      loop.call_soon_threadsafe(loop.stop)
      thread.join()
      loop.close()

  def destroy(self):
    self.running = False

  def _route(self, action):
    """
    Enqueues the action on intended recipient(s)
    """
    # "send" by ultimately calling the receiver's "_receive"
    recipients = []
    if 'to' in action:
      # if receiver is specified send to only that channel
      recipients = [
        channel for channel in self.channels
        if channel.id() == action['to']
      ]
    else:
      # if it isn't send to all _but_ the sender
      recipients = [
        channel for channel in self.channels
        if channel.id() != action['from']
      ]
    
    # send to all, setting the 'to' field to the recipient's id
    for recipient in recipients:
      action['to'] = recipient.id()
      recipient._receive(action)

  def _get_help__sync(self, action=None):
    """
    Returns a help object immediately without forwarding messages
    """
    help = [
      channel._get_help(action)
      for channel in [self] + self.channels
    ]
    return help
