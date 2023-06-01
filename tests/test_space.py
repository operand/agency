import time
import unittest


def test_create_destroy(space):
  """
  Tests basic creation and destruction of a Space.
  """
  # Just wait for 2 seconds here and the fixture handles the rest
  time.sleep(2)


if __name__ == '__main__':
  unittest.main()
