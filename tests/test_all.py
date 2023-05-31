import threading
import time
import unittest
from everything.channels.channel import Channel
from everything.things.space import Space
from everything.things.operator import Operator


class TestChannel(Channel):
  pass


class TestAll(unittest.TestCase):
  def setUp(self):
    # Create space in a separate thread
    self.space = Space([
      TestChannel(
        Operator("test"),
      ),
    ])
    self.thread = threading.Thread(target=self.space.create, daemon=True)
    self.thread.start()

  def tearDown(self) -> None:
    self.space.destroy()
    # Wait for the thread to complete
    self.thread.join()
    self.assertFalse(self.space.running)  # Assert that the loop has stopped

  def test_create_space(self):
    """
    Tests basic creation and destruction of a Space.
    """
    time.sleep(2)  # Wait for 2 seconds in the main thread



if __name__ == '__main__':
  unittest.main()