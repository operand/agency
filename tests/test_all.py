import threading
import time
import unittest
from channels.channel import Channel
from things.space import Space
from things.operator import Operator


class TestChannel(Channel):
  pass


class TestAll(unittest.TestCase):
  def test_create_space(self):
    """
    Tests basic creation and destruction of a Space.
    """
    space = Space([
      TestChannel(
        Operator("test"),
      ),
    ])
    # Start create() in a separate thread.
    thread = threading.Thread(target=space.create, daemon=True)
    thread.start()
    print(f"thread started {thread}")
    time.sleep(2)  # Wait for 2 seconds in the main thread.
    space.destroy()
    # Wait for the thread to complete.
    thread.join()
    self.assertFalse(space.running)  # Assert that the loop has stopped.


if __name__ == '__main__':
  unittest.main()