import threading
import time
from unittest.mock import AsyncMock, create_autospec
from everything.channels.web_channel import WebChannel
from everything.things.operator import Operator
from everything.things.space import Space
import pytest


def space(channels):
  space = Space(channels)
  thread = threading.Thread(target=space.create, daemon=True)
  thread.start()

  # wait for the space to fully start
  while not space.created.is_set():
    time.sleep(0.1)

  yield space

  space.destroy()
  assert space.destructing.is_set()
  thread.join()


@pytest.fixture
def empty_space():
  yield space([])


@pytest.fixture
def chat_space():
  mock_webchannel = create_autospec(WebChannel)
  mock_webchannel._process.return_value = AsyncMock()
  mock_chattychannel = create_autospec(WebChannel)
  mock_chattychannel._process.return_value = AsyncMock()

  yield space([
    mock_webchannel(Operator("Webster")),
    mock_chattychannel(Operator("Chatty")),
  ])
