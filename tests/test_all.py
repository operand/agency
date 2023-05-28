import asyncio
import unittest
from src._operator_ import Operator
from src.space import Space


class TestOperator(Operator):
  pass


# TODO finish this test
class TestAll(unittest.TestCase):
  def test_space_can_start_and_stop(self):
    # start space
    result = asyncio.run(Space([
      TestOperator(),
    ]).start())


if __name__ == '__main__':
  unittest.main()
