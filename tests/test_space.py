import threading
import time
import unittest
from unittest.mock import AsyncMock, Mock, create_autospec
from everything.channels.channel import Channel
from everything.things.space import Space
from everything.things.operator import Operator




class TestSpace(unittest.TestCase):
  def setUp(self):
    # Create space in a separate thread
    self.mock_channel = create_autospec(Channel)
    self.mock_channel._process.return_value = AsyncMock()
    self.space = Space([
      self.mock_channel(Operator("test")),
    ])
    self.thread = threading.Thread(target=self.space.create, daemon=True)
    self.thread.start()

  def tearDown(self) -> None:
    self.space.destroy()
    # Wait for the thread to complete
    self.thread.join()
    self.assertFalse(self.space.running)  # Assert that the loop has stopped

  def test_create_destroy(self):
    """
    Tests basic creation and destruction of a Space.
    """
    time.sleep(2)  # Wait for 2 seconds in the main thread


if __name__ == '__main__':
  unittest.main()